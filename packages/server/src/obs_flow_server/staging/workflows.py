"""Staging batch lifecycle: building blocks first, I/O procedures last."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from obs_flow_common.messages import ReviewDetail, StagingDetail

from accounts.helpers import build_user_dto
from core.gitea import merge_pull_request
from core.models import Project
from pull_requests.models import PullRequest
from reviews.models import ReviewScope
from reviews.workflows import build_reviewer_dto_from_fields
from reviews.workflows import parse_reviewer
from staging.models import (
    StagingBatch,
    StagingBatchRevision,
    StagingBatchRevisionPullRequest,
    StagingReview,
)


# =====================================================================
# Building blocks (entity-level, no external I/O)
# =====================================================================


def compute_staging_fingerprint(pr_revisions) -> str:
    """
    Computes a deterministic SHA-256 fingerprint of the staging batch.
    """
    from staging.fingerprint import StagingBatchPayload

    pr_fingerprints = []
    for pr_rev in pr_revisions:
        if not pr_rev.fingerprint:
            raise ValueError(f"PullRequestRevision {pr_rev.id} is missing a fingerprint.")
        pr_fingerprints.append(pr_rev.fingerprint)

    payload = StagingBatchPayload(
        pr_revisions=pr_fingerprints,
    )
    return payload.compute_fingerprint()


def create_staging_revision(batch: StagingBatch, pr_revisions) -> StagingBatchRevision:
    """
    Creates a new StagingBatchRevision for the given StagingBatch and list of PullRequestRevisions.
    If the latest revision has the exact same fingerprint, it returns the existing one.
    Otherwise, it increments the revision number, creates the new revision in draft mode with debounce timer,
    and links the PR revisions. Reviews are not provisioned while in draft.
    """
    fingerprint = compute_staging_fingerprint(pr_revisions)
    latest_rev = batch.latest_revision

    if latest_rev and latest_rev.fingerprint == fingerprint:
        return latest_rev

    timeout_minutes = batch.project.effective_review_debounce_minutes
    rev_number = (latest_rev.revision_number + 1) if latest_rev else 1

    if timeout_minutes == 0:
        rev_is_draft = False
        rev_draft_expires_at = None
    else:
        rev_is_draft = True
        rev_draft_expires_at = timezone.now() + timedelta(minutes=timeout_minutes)

    new_rev = StagingBatchRevision.objects.create(
        staging_batch=batch,
        revision_number=rev_number,
        fingerprint=fingerprint,
        is_draft=rev_is_draft,
        draft_expires_at=rev_draft_expires_at,
    )

    for pr_rev in pr_revisions:
        StagingBatchRevisionPullRequest.objects.create(
            staging_batch_revision=new_rev,
            pull_request_revision=pr_rev,
        )

    if not rev_is_draft:
        provision_reviews_for_staging_revision(new_rev)

    return new_rev


@transaction.atomic
def provision_reviews_for_staging_revision(revision: StagingBatchRevision) -> list[StagingReview]:
    """
    Provisions reviews for a StagingBatchRevision based on ReviewConfig if no reviews exist.
    While a revision is in draft mode, no review records are created.
    Existing reviews are never re-provisioned.
    Evaluates scopes against changed files and supports decision inheritance.
    """
    rev = StagingBatchRevision.objects.select_for_update().get(pk=revision.pk)
    if rev.is_draft:
        return []
    if rev.reviews.exists():
        return list(rev.reviews.all())

    from reviews.models import ReviewConfig
    configs = ReviewConfig.objects.filter(project=rev.staging_batch.project, type="staging").select_related("scope")
    created_reviews = []
    if configs.exists():
        config_to_review = {}

        batch = rev.staging_batch
        changed_files = rev.get_changed_files()
        prev_rev = (
            batch.revisions.filter(revision_number__lt=rev.revision_number)
            .order_by("-revision_number")
            .first()
        )
        inter_files = rev.get_inter_revision_changed_files(prev_rev) if prev_rev else changed_files

        for config in configs:
            scope = config.scope
            is_in_scope = scope.evaluate(changed_files)

            if not is_in_scope:
                review = StagingReview.objects.create(
                    revision=rev,
                    reviewer_user=config.reviewer_user,
                    reviewer_group=config.reviewer_group,
                    dynamic_role=config.dynamic_role,
                    scope=scope,
                    state=StagingReview.State.SKIPPED,
                    is_inherited=False,
                )
            else:
                prev_review = None
                if prev_rev:
                    prev_review = StagingReview.objects.filter(
                        revision=prev_rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                    ).first()

                if (
                    prev_review
                    and prev_review.scope_id == scope.id
                    and prev_review.state != StagingReview.State.SKIPPED
                    and not scope.evaluate(inter_files)
                ):
                    review = StagingReview.objects.create(
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
                    review = StagingReview.objects.create(
                        revision=rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                        scope=scope,
                        state=StagingReview.State.WAITING,
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
            if review.state == StagingReview.State.WAITING:
                prereqs = review.depends_on.all()
                if not prereqs.exists() or all(
                    p.state in (StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN, StagingReview.State.SKIPPED)
                    for p in prereqs
                ):
                    review.state = StagingReview.State.PENDING
                    review.save(update_fields=["state"])

    return created_reviews


@transaction.atomic
def mark_staging_ready_for_review(revision: StagingBatchRevision) -> None:
    """
    Transitions a StagingBatchRevision out of draft mode and provisions reviews.
    """
    rev = StagingBatchRevision.objects.select_for_update().get(pk=revision.pk)
    if not rev.is_draft and rev.draft_expires_at is None:
        return
    rev.is_draft = False
    rev.draft_expires_at = None
    rev.save(update_fields=["is_draft", "draft_expires_at"])
    revision.is_draft = False
    revision.draft_expires_at = None
    provision_reviews_for_staging_revision(rev)


@transaction.atomic
def mark_staging_draft(revision: StagingBatchRevision) -> None:
    """
    Transitions a StagingBatchRevision into manual draft mode without debounce timer.
    Existing reviews are not modified or removed.
    """
    rev = StagingBatchRevision.objects.select_for_update().get(pk=revision.pk)
    if rev.is_draft and rev.draft_expires_at is None:
        return
    rev.is_draft = True
    rev.draft_expires_at = None
    rev.save(update_fields=["is_draft", "draft_expires_at"])
    revision.is_draft = True
    revision.draft_expires_at = None


def batch_to_detail(batch: StagingBatch) -> StagingDetail:
    latest_rev = batch.latest_revision
    if latest_rev:
        prs = [
            bpr.pull_request_revision.pull_request.text_id
            for bpr in latest_rev.revision_pull_requests.all()
        ]
        latest_rev_num = latest_rev.revision_number
        fingerprint = latest_rev.fingerprint
    else:
        prs = []
        latest_rev_num = None
        fingerprint = None

    creator_dto = build_user_dto(batch.author) if batch.author else None
    return StagingDetail(
        id=batch.id,
        state=batch.state,
        creator=creator_dto,
        title=batch.title,
        target_project=batch.project.name,
        pull_requests=prs,
        embargo_date=batch.embargo_date.isoformat() if batch.embargo_date else None,
        release_date=batch.release_date.isoformat() if batch.release_date else None,
        latest_revision=latest_rev_num,
        fingerprint=fingerprint,
        is_draft=batch.is_draft,
    )


def review_to_detail(review: StagingReview) -> ReviewDetail:
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


def get_review_for_request(batch: StagingBatch, reviewer_str: str | None) -> StagingReview:
    latest_rev = batch.latest_revision
    if not latest_rev:
        raise ValueError(f"Staging batch #{batch.id} has no revisions.")
    user, group, role = parse_reviewer(reviewer_str, default_admin=True)
    if user:
        review = StagingReview.objects.filter(revision=latest_rev, reviewer_user=user).first()
        if review is None:
            review = StagingReview.objects.create(
                revision=latest_rev,
                reviewer_user=user,
                state=StagingReview.State.PENDING,
                scope=ReviewScope.objects.get(name="global"),
            )
    elif group:
        review = StagingReview.objects.filter(revision=latest_rev, reviewer_group=group).first()
        if review is None:
            review = StagingReview.objects.create(
                revision=latest_rev,
                reviewer_group=group,
                state=StagingReview.State.PENDING,
                scope=ReviewScope.objects.get(name="global"),
            )
    else:
        review = StagingReview.objects.filter(revision=latest_rev, dynamic_role=role).first()
        if review is None:
            review = StagingReview.objects.create(
                revision=latest_rev,
                dynamic_role=role,
                state=StagingReview.State.PENDING,
                scope=ReviewScope.objects.get(name="global"),
            )
    return review


def batch_member_prs(batch: StagingBatch) -> list[PullRequest]:
    """Current member PRs of the batch, from its latest revision."""
    latest_rev = batch.latest_revision
    if not latest_rev:
        return []
    return [
        bpr.pull_request_revision.pull_request
        for bpr in latest_rev.revision_pull_requests.all()
    ]


def find_conflicts(batch: StagingBatch, prs: list[PullRequest]) -> list[dict]:
    """PRs that are already contained in another open staging batch."""
    conflicts = []
    for pr in prs:
        other_open_batches = StagingBatch.objects.filter(
            state__in=[StagingBatch.State.COLLECTING, StagingBatch.State.IN_PROGRESS],
            revisions__revision_pull_requests__pull_request_revision__pull_request=pr
        ).exclude(id=batch.id).distinct()

        if other_open_batches.exists():
            conflicts.append({
                "pr": pr,
                "other_batches": other_open_batches,
            })
    return conflicts


def staging_merge_blockers(batch: StagingBatch) -> tuple[bool, str | None, list, list]:
    if batch.state == StagingBatch.State.MERGED:
        return False, "Staging batch is already merged.", [], []

    latest_rev = batch.latest_revision
    if not latest_rev:
        return False, "Staging batch has no revisions.", [], []

    if latest_rev.is_draft:
        return False, "Staging batch is currently in draft mode and cannot be merged.", [], []

    reviews = list(latest_rev.reviews.all())
    unapproved = latest_rev.reviews.exclude(state__in=[StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN])
    if unapproved.exists():
        names = [r.reviewer_name for r in unapproved]
        return False, f"Unapproved reviews: {', '.join(names)}.", reviews, []

    prs = [bpr.pull_request_revision.pull_request for bpr in latest_rev.revision_pull_requests.all()]
    for pr in prs:
        if pr.is_draft:
            return False, f"Pull request #{pr.number} in batch is in draft mode.", reviews, prs
        if pr.is_mergeable is False:
            return False, f"Pull request #{pr.number} in batch has merge conflicts.", reviews, prs

    return True, None, reviews, prs


# =====================================================================
# Procedures (multi-entity / external-system I/O)
# =====================================================================


def create_batch(project: Project, title, author, embargo_date, release_date) -> StagingDetail:
    batch = StagingBatch.objects.create(
        project=project,
        title=title,
        author=author,
        embargo_date=timezone.datetime.fromisoformat(embargo_date) if embargo_date else None,
        release_date=timezone.datetime.fromisoformat(release_date) if release_date else None,
    )

    # Create revision 1 (empty)
    create_staging_revision(batch, [])

    return batch_to_detail(batch)


def update_batch(batch_id: int, title=None, embargo_date=None, release_date=None) -> StagingBatch:
    batch = StagingBatch.objects.get(id=batch_id)

    if title is not None:
        batch.title = title
    if embargo_date is not None:
        if embargo_date == "":
            batch.embargo_date = None
        elif isinstance(embargo_date, str):
            batch.embargo_date = timezone.datetime.fromisoformat(embargo_date)
        else:
            batch.embargo_date = embargo_date

    if release_date is not None:
        if release_date == "":
            batch.release_date = None
        elif isinstance(release_date, str):
            batch.release_date = timezone.datetime.fromisoformat(release_date)
        else:
            batch.release_date = release_date

    batch.save()
    return batch


def rebuild_batch_revision(batch: StagingBatch, prs: list[PullRequest]) -> StagingBatchRevision:
    """Collect the latest revision of each PR and create the successor batch revision."""
    pr_revisions = []
    for pr in prs:
        latest_pr_rev = pr.latest_revision
        if latest_pr_rev:
            pr_revisions.append(latest_pr_rev)

    return create_staging_revision(batch, pr_revisions)


def add_prs_to_batch(batch: StagingBatch, pr_text_ids: list[str]) -> list[str]:
    # Validate that all requested PRs target the same project as the batch
    resolved_prs = []
    for pr_id in pr_text_ids:
        pr = PullRequest.objects.get_by_text_id(pr_id)
        if pr.target_project != batch.project:
            raise ValueError(
                f"Pull request '{pr_id}' belongs to project '{pr.target_project.name}', "
                f"which does not match staging batch project '{batch.project.name}'."
            )
        resolved_prs.append(pr)

    current_prs = batch_member_prs(batch)
    for pr in resolved_prs:
        if pr not in current_prs:
            current_prs.append(pr)

    rebuild_batch_revision(batch, current_prs)

    return [pr.text_id for pr in current_prs]


def remove_prs_from_batch(batch: StagingBatch, pr_text_ids: list[str]) -> list[str]:
    current_prs = batch_member_prs(batch)

    for pr_id in pr_text_ids:
        try:
            pr = PullRequest.objects.get_by_text_id(pr_id)
            if pr in current_prs:
                current_prs.remove(pr)
        except Exception:
            pass

    rebuild_batch_revision(batch, current_prs)

    return [pr.text_id for pr in current_prs]


def rebuild_batches_for_pr_revision(pr: PullRequest, new_pr_revision) -> None:
    """Update any StagingBatches containing this PR to use the new PullRequestRevision."""
    affected_batches = StagingBatch.objects.filter(
        revisions__revision_pull_requests__pull_request_revision__pull_request=pr
    ).distinct()

    for batch in affected_batches:
        latest_rev = batch.latest_revision
        if latest_rev:
            latest_pr_revs = [
                bpr.pull_request_revision
                for bpr in latest_rev.revision_pull_requests.all()
            ]
            latest_prs = [r.pull_request for r in latest_pr_revs]
            if pr in latest_prs:
                updated_pr_revs = []
                for r in latest_pr_revs:
                    if r.pull_request == pr:
                        updated_pr_revs.append(new_pr_revision)
                    else:
                        updated_pr_revs.append(r)
                create_staging_revision(batch, updated_pr_revs)


def merge_batches(staging_ids: list[int]) -> tuple[list[StagingDetail], list[str]]:
    sorted_ids = sorted(set(staging_ids))

    with transaction.atomic():
        # Lock all requested batches in deterministic primary-key order to prevent deadlocks
        batches_dict = {
            b.id: b
            for b in StagingBatch.objects.select_for_update().filter(id__in=sorted_ids).order_by("id")
        }

        errors = []
        batches_to_merge = []

        # 1. Validation pass: validate all batches and collect all errors
        for batch_id in staging_ids:
            batch = batches_dict.get(batch_id)
            if not batch:
                errors.append(f"Staging batch #{batch_id} does not exist.")
                continue

            if batch.state == StagingBatch.State.MERGED:
                errors.append(f"Staging batch #{batch_id} is already merged.")
                continue

            latest_rev = batch.latest_revision
            if not latest_rev:
                errors.append(f"Staging batch #{batch_id} has no revisions.")
                continue

            if latest_rev.is_draft:
                errors.append(f"Staging batch #{batch_id} is currently in draft mode and cannot be merged.")
                continue

            # Validate that all reviews on the latest revision are resolved (ACCEPTED or OVERRIDDEN)
            reviews = latest_rev.reviews.all()
            unapproved_reviews = reviews.exclude(
                state__in=[StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN]
            )
            if unapproved_reviews.exists():
                unapproved_names = [
                    str(r.reviewer_user or r.reviewer_group or r.dynamic_role)
                    for r in unapproved_reviews
                ]
                errors.append(
                    f"Staging batch #{batch_id} cannot be merged because the following reviews are not approved: {', '.join(unapproved_names)}."
                )
                continue

            batches_to_merge.append((batch, latest_rev))

        if errors:
            return [], errors

        # 2. Execution pass: all batches validated, now perform atomic merges
        updated_batches = []
        for batch, latest_rev in batches_to_merge:
            batch_prs = [
                bpr.pull_request_revision.pull_request
                for bpr in latest_rev.revision_pull_requests.all()
            ]

            for pr in batch_prs:
                if pr.state != PullRequest.State.MERGED:
                    try:
                        merge_pull_request(pr.target.owner, pr.target.repo, pr.number)
                    except ValueError as e:
                        return [], [str(e)]
                    pr.state = PullRequest.State.MERGED
                    pr.save(update_fields=["state"])

            # Update batch state and closed_at
            batch.state = StagingBatch.State.MERGED
            batch.closed_at = timezone.now()
            batch.save(update_fields=["state", "closed_at"])

            updated_batches.append(batch_to_detail(batch))

        return updated_batches, []
