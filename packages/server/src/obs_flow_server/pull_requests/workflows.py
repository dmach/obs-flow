"""Pull request lifecycle: building blocks first, I/O procedures last."""

import json
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from obs_flow_common.messages import PRDetail, PRSyncRequest, PRSyncResponse, ReviewDetail

from accounts.helpers import build_user_dto
from accounts.models import User
from core.gitea import merge_pull_request
from core.models import GitMapping, Project
from pull_requests.models import PullRequest, PullRequestRevision, PullRequestReview
from reviews.models import ReviewScope
from reviews.workflows import build_reviewer_dto_from_fields
from reviews.workflows import parse_reviewer


# =====================================================================
# Building blocks (entity-level, no external I/O)
# =====================================================================


def review_to_detail(review: PullRequestReview) -> ReviewDetail:
    reviewer_dto = build_reviewer_dto_from_fields(
        review.reviewer_user,
        review.reviewer_group,
        review.dynamic_role,
    )
    actor_dto = build_user_dto(review.actor) if review.actor else None
    scope_name = review.scope.name

    return ReviewDetail(
        reviewer=reviewer_dto,
        state=review.state,
        actor=actor_dto,
        when=review.updated_at.isoformat(),
        why=review.justification,
        scope=scope_name,
        is_inherited=review.is_inherited,
    )


def get_review_for_request(revision: PullRequestRevision, reviewer_str: str | None) -> PullRequestReview:
    user, group, role = parse_reviewer(reviewer_str, default_admin=True)
    if user:
        review = PullRequestReview.objects.filter(revision=revision, reviewer_user=user).first()
        if review is None:
            review = PullRequestReview.objects.create(
                revision=revision,
                reviewer_user=user,
                state=PullRequestReview.State.PENDING,
                scope=ReviewScope.objects.get(name="global"),
            )
    elif group:
        review = PullRequestReview.objects.filter(revision=revision, reviewer_group=group).first()
        if review is None:
            review = PullRequestReview.objects.create(
                revision=revision,
                reviewer_group=group,
                state=PullRequestReview.State.PENDING,
                scope=ReviewScope.objects.get(name="global"),
            )
    else:
        review = PullRequestReview.objects.filter(revision=revision, dynamic_role=role).first()
        if review is None:
            review = PullRequestReview.objects.create(
                revision=revision,
                dynamic_role=role,
                state=PullRequestReview.State.PENDING,
                scope=ReviewScope.objects.get(name="global"),
            )
    return review


@transaction.atomic
def provision_reviews_for_revision(revision: PullRequestRevision) -> list[PullRequestReview]:
    """
    Provisions reviews for a PullRequestRevision based on ReviewConfig if no reviews exist.
    While a revision is in draft mode, no review records are created.
    Existing reviews are never re-provisioned.
    Evaluates scopes against changed files and supports decision inheritance.
    """
    rev = PullRequestRevision.objects.select_for_update().get(pk=revision.pk)
    if rev.is_draft:
        return []
    if rev.reviews.exists():
        return list(rev.reviews.all())

    from reviews.models import ReviewConfig

    pr = rev.pull_request
    git_mapping = pr.target
    project = git_mapping.target_project
    if git_mapping.project_id:
        config_type = ReviewConfig.ConfigType.PROJECT
    elif git_mapping.package_id:
        config_type = ReviewConfig.ConfigType.PACKAGE
    else:
        config_type = None

    created_reviews = []
    if project and config_type:
        configs = ReviewConfig.objects.filter(project=project, type=config_type).select_related("scope")
        config_to_review = {}

        changed_files = rev.get_changed_files()
        prev_rev = (
            pr.revisions.filter(revision_number__lt=rev.revision_number)
            .order_by("-revision_number")
            .first()
        )
        inter_files = rev.get_inter_revision_changed_files(prev_rev) if prev_rev else changed_files

        for config in configs:
            scope = config.scope
            is_in_scope = scope.evaluate(changed_files)

            if not is_in_scope:
                review = PullRequestReview.objects.create(
                    revision=rev,
                    reviewer_user=config.reviewer_user,
                    reviewer_group=config.reviewer_group,
                    dynamic_role=config.dynamic_role,
                    scope=scope,
                    state=PullRequestReview.State.SKIPPED,
                    is_inherited=False,
                )
            else:
                prev_review = None
                if prev_rev:
                    prev_review = PullRequestReview.objects.filter(
                        revision=prev_rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                    ).first()

                if (
                    prev_review
                    and prev_review.scope_id == scope.id
                    and prev_review.state != PullRequestReview.State.SKIPPED
                    and not scope.evaluate(inter_files)
                ):
                    review = PullRequestReview.objects.create(
                        revision=rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                        scope=scope,
                        state=prev_review.state,
                        actor=prev_review.actor,
                        justification=prev_review.justification,
                        is_inherited=True,
                    )
                else:
                    review = PullRequestReview.objects.create(
                        revision=rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                        scope=scope,
                        state=PullRequestReview.State.WAITING,
                        is_inherited=False,
                    )

            config_to_review[config] = review
            created_reviews.append(review)

        # Set up dependencies between the created reviews
        for config, review in config_to_review.items():
            for dep_config in config.depends_on.all():
                if dep_config in config_to_review:
                    review.depends_on.add(config_to_review[dep_config])

        # Reviews with no unresolved dependencies start as PENDING, others remain WAITING
        for review in created_reviews:
            if review.state == PullRequestReview.State.WAITING:
                prereqs = review.depends_on.all()
                if not prereqs.exists() or all(
                    p.state in (PullRequestReview.State.ACCEPTED, PullRequestReview.State.OVERRIDDEN, PullRequestReview.State.SKIPPED)
                    for p in prereqs
                ):
                    review.state = PullRequestReview.State.PENDING
                    review.save(update_fields=["state"])

    return created_reviews


@transaction.atomic
def mark_ready_for_review(revision: PullRequestRevision) -> None:
    """
    Transitions a PullRequestRevision out of draft mode and provisions reviews.
    """
    rev = PullRequestRevision.objects.select_for_update().get(pk=revision.pk)
    if not rev.is_draft and rev.draft_expires_at is None:
        return
    rev.is_draft = False
    rev.draft_expires_at = None
    rev.save(update_fields=["is_draft", "draft_expires_at"])
    revision.is_draft = False
    revision.draft_expires_at = None
    provision_reviews_for_revision(rev)


@transaction.atomic
def mark_draft(revision: PullRequestRevision) -> None:
    """
    Transitions a PullRequestRevision into manual draft mode without debounce timer.
    Existing reviews are not modified or removed.
    """
    rev = PullRequestRevision.objects.select_for_update().get(pk=revision.pk)
    if rev.is_draft and rev.draft_expires_at is None:
        return
    rev.is_draft = True
    rev.draft_expires_at = None
    rev.save(update_fields=["is_draft", "draft_expires_at"])
    revision.is_draft = True
    revision.draft_expires_at = None


def pr_to_detail(pr: PullRequest, latest_revision: PullRequestRevision | None = None, id: str | None = None) -> PRDetail:
    return PRDetail(
        id=id or pr.text_id,
        title=pr.title,
        state=pr.state,
        is_draft=pr.is_draft,
        is_mergeable=pr.is_mergeable,
        author=build_user_dto(pr.author),
        latest_revision=latest_revision.revision_number if latest_revision else 0,
        head_sha=latest_revision.head_sha if latest_revision else "",
        base_sha=latest_revision.base_sha if latest_revision else "",
    )


def pr_merge_blockers(pr: PullRequest) -> tuple[bool, str | None, list[str]]:
    warnings = []
    target_project = pr.target_project
    if target_project and target_project.workflow_type == Project.WorkflowType.STAGING:
        return False, f"Project '{target_project.name}' uses the staging workflow. Direct merges are disabled.", []

    if pr.state == PullRequest.State.MERGED:
        return False, f"Pull request #{pr.number} is already merged.", []

    if pr.state == PullRequest.State.CLOSED:
        return False, f"Pull request #{pr.number} is closed.", []

    latest_rev = pr.latest_revision
    if pr.is_draft or (latest_rev and latest_rev.is_draft):
        return False, f"Pull request #{pr.number} is in draft mode and cannot be merged.", []

    if pr.is_mergeable is False:
        return False, f"Pull request #{pr.number} has merge conflicts and cannot be merged.", []

    if latest_rev:
        reviews = latest_rev.reviews.all()
        if reviews.exists():
            unapproved = reviews.exclude(state__in=[PullRequestReview.State.ACCEPTED, PullRequestReview.State.OVERRIDDEN])
            if unapproved.exists():
                names = [r.reviewer_name for r in unapproved]
                return False, f"Reviews not approved: {', '.join(names)}.", []

    return True, None, warnings


# =====================================================================
# Procedures (multi-entity / external-system I/O)
# =====================================================================


def sync_pull_request(req: PRSyncRequest) -> PRSyncResponse:
    # Fetch from Gitea
    url = f"{settings.GITEA_URL.rstrip('/')}/api/v1/repos/{req.owner}/{req.repo}/pulls/{req.number}"
    headers = {
        "Authorization": f"token {settings.GITEA_TOKEN}",
        "Accept": "application/json"
    }

    try:
        req_obj = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req_obj) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as e:
        raise Exception(f"Failed to fetch PR from Gitea: {e}")

    # Extract data
    title = data.get("title")
    draft = data.get("draft", False)
    mergeable = data.get("mergeable")
    head_sha = data.get("head", {}).get("sha")
    base_sha = data.get("base", {}).get("sha")
    author_login = data.get("user", {}).get("login")
    state_str = data.get("state", "open")

    # Map state
    if state_str == "closed":
        if data.get("merged"):
            pr_state = PullRequest.State.MERGED
        else:
            pr_state = PullRequest.State.CLOSED
    else:
        pr_state = PullRequest.State.OPEN

    # Get or create author
    author, _ = User.objects.get_or_create(
        username=author_login,
        defaults={
            "username_lower": author_login.lower(),
            "account_type": User.AccountType.HUMAN
        }
    )

    # Find GitMapping
    base_branch = data.get("base", {}).get("ref", "main")
    try:
        git_mapping = GitMapping.objects.get(
            owner__iexact=req.owner,
            repo__iexact=req.repo,
            branch=base_branch
        )
    except GitMapping.DoesNotExist:
        raise Exception(f"No GitMapping found for {req.owner}/{req.repo}:{base_branch}")

    # Get or create PR
    pr, created = PullRequest.objects.get_or_create(
        target=git_mapping,
        number=req.number,
        defaults={
            "author": author,
            "title": title,
            "is_mergeable": mergeable,
            "state": pr_state,
            "source_owner": data.get("head", {}).get("repo", {}).get("owner", {}).get("login", req.owner),
            "source_repo": data.get("head", {}).get("repo", {}).get("name", req.repo),
            "source_branch": data.get("head", {}).get("ref", "unknown"),
        }
    )

    if not created:
        # Update fields
        pr.title = title
        pr.is_mergeable = mergeable
        pr.state = pr_state
        pr.save()

    # Check revisions
    from pull_requests.fingerprint import PRRevisionPayload

    pr_payload = PRRevisionPayload(
        head_sha=head_sha,
        base_sha=base_sha,
        target_branch=pr.target.branch,
    )
    fingerprint = pr_payload.compute_fingerprint()

    target_project = pr.target.target_project
    timeout_minutes = target_project.effective_review_debounce_minutes if target_project else settings.REVIEW_DEBOUNCE_MINUTES
    latest_revision = pr.latest_revision
    if not latest_revision or latest_revision.fingerprint != fingerprint:
        rev_number = (latest_revision.revision_number + 1) if latest_revision else 1

        if draft:
            rev_is_draft = True
            rev_draft_expires_at = None
        elif timeout_minutes == 0:
            rev_is_draft = False
            rev_draft_expires_at = None
        else:
            rev_is_draft = True
            rev_draft_expires_at = timezone.now() + timedelta(minutes=timeout_minutes)

        latest_revision = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=rev_number,
            head_sha=head_sha,
            base_sha=base_sha,
            fingerprint=fingerprint,
            is_draft=rev_is_draft,
            draft_expires_at=rev_draft_expires_at,
        )

        if not rev_is_draft:
            provision_reviews_for_revision(latest_revision)

        # Update any StagingBatches containing this PR to use the new PullRequestRevision
        # (function-level import: staging.workflows imports pull_requests.workflows)
        from staging.workflows import rebuild_batches_for_pr_revision

        rebuild_batches_for_pr_revision(pr, latest_revision)
    else:
        # Same fingerprint (no new push). Check if upstream draft state changed.
        if not draft and latest_revision.is_draft and latest_revision.draft_expires_at is None:
            # Transitioned from manual draft to ready in upstream forge
            mark_ready_for_review(latest_revision)
        elif draft and not latest_revision.is_draft:
            # Upstream toggled back to draft
            latest_revision.is_draft = True
            latest_revision.draft_expires_at = None
            latest_revision.save(update_fields=["is_draft", "draft_expires_at"])

    return PRSyncResponse(
        pull_request=pr_to_detail(
            pr,
            latest_revision,
            id=f"{req.owner}/{req.repo}#{req.number}",
        )
    )


def merge_pull_requests(pr_text_ids: list[str]) -> tuple[list[PRDetail], list[str]]:
    with transaction.atomic():
        # First resolve PR objects to get DB IDs for deterministic ordering
        prs_by_text_id = {}
        errors = []
        for pr_id in pr_text_ids:
            try:
                pr = PullRequest.objects.get_by_text_id(pr_id)
                prs_by_text_id[pr_id] = pr
            except (PullRequest.DoesNotExist, ValueError) as e:
                errors.append(str(e))

        # Lock PRs in deterministic DB id order to prevent deadlocks
        resolved_db_ids = sorted(p.id for p in prs_by_text_id.values())
        locked_prs = {
            p.id: p
            for p in PullRequest.objects.select_for_update().filter(id__in=resolved_db_ids).order_by("id")
        }

        prs_to_merge = []
        # Validate all PRs and collect all errors
        for pr_id in pr_text_ids:
            pr = prs_by_text_id.get(pr_id)
            if not pr:
                continue

            target_project = pr.target_project
            if target_project and target_project.workflow_type == Project.WorkflowType.STAGING:
                errors.append(
                    f"Direct merges are not allowed for project '{target_project.name}' because it uses the staging workflow. "
                    "Please merge via a staging batch."
                )
                continue

            if pr.state == PullRequest.State.MERGED:
                errors.append(f"Pull request {pr_id} is already merged.")
                continue

            latest_revision = pr.latest_revision
            if pr.is_draft or (latest_revision and latest_revision.is_draft):
                errors.append(f"Pull request {pr_id} is in draft mode and cannot be merged.")
                continue

            prs_to_merge.append((pr_id, pr))

        if errors:
            return [], errors

        # All valid, execute merges
        updated_prs = []
        for pr_id, pr in prs_to_merge:
            try:
                merge_pull_request(pr.target.owner, pr.target.repo, pr.number)
            except ValueError as e:
                return [], [str(e)]

            pr.state = PullRequest.State.MERGED
            pr.save(update_fields=["state"])

            latest_revision = pr.latest_revision
            updated_prs.append(pr_to_detail(pr, latest_revision, id=pr_id))

        return updated_prs, []
