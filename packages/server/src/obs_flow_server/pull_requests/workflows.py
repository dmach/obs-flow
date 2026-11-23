"""Pull request lifecycle: building blocks first, I/O procedures last."""

import json
import urllib.error
import urllib.request
from django.conf import settings
from django.db import transaction

from obs_flow_common.messages import PRDetail, PRSyncRequest, PRSyncResponse

from accounts.helpers import build_user_dto
from accounts.models import User
from core.gitea import merge_pull_request
from core.models import GitMapping, Project
from pull_requests.models import PullRequest, PullRequestRevision, PullRequestReview
from reviews.workflows import initial_draft_state, mark_draft as _mark_draft, mark_ready, provision_reviews_for


# =====================================================================
# Building blocks (entity-level, no external I/O)
# =====================================================================


def provision_reviews_for_revision(revision: PullRequestRevision) -> list[PullRequestReview]:
    """
    Provisions reviews for a PullRequestRevision based on ReviewConfig if no reviews exist.
    While a revision is in draft mode, no review records are created.
    Existing reviews are never re-provisioned.
    Evaluates scopes against changed files and supports decision inheritance.
    """
    from reviews.models import ReviewConfig

    pr = revision.pull_request
    git_mapping = pr.target
    project = git_mapping.target_project
    if git_mapping.project_id:
        config_type = ReviewConfig.ConfigType.PROJECT
    elif git_mapping.package_id:
        config_type = ReviewConfig.ConfigType.PACKAGE
    else:
        config_type = None

    if project and config_type:
        configs = ReviewConfig.objects.filter(project=project, type=config_type).select_related("scope")
    else:
        configs = ReviewConfig.objects.none()

    prev_rev = (
        pr.revisions.filter(revision_number__lt=revision.revision_number)
        .order_by("-revision_number")
        .first()
    )
    return provision_reviews_for(
        revision,
        configs,
        review_model=PullRequestReview,
        revision_model=PullRequestRevision,
        prev_rev=prev_rev,
    )


def mark_ready_for_review(revision: PullRequestRevision) -> None:
    """
    Transitions a PullRequestRevision out of draft mode and provisions reviews.
    """
    mark_ready(revision, revision_model=PullRequestRevision, provision_fn=provision_reviews_for_revision)


def mark_draft(revision: PullRequestRevision) -> None:
    """
    Transitions a PullRequestRevision into manual draft mode without debounce timer.
    Existing reviews are not modified or removed.
    """
    _mark_draft(revision, revision_model=PullRequestRevision)


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

        rev_is_draft, rev_draft_expires_at = initial_draft_state(draft, timeout_minutes)

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
