"""Staging batch lifecycle: building blocks first, I/O procedures last."""

from django.db import transaction
from django.utils import timezone

from obs_flow_common.messages import StagingDetail

from accounts.helpers import build_user_dto
from core.models import Project
from pull_requests.models import PullRequest
from pull_requests.workflows import execute_pr_merge
from reviews.workflows import (
    get_or_create_review,
    initial_draft_state,
    mark_draft,
    mark_ready,
    provision_reviews_for,
)
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

    rev_is_draft, rev_draft_expires_at = initial_draft_state(False, timeout_minutes)

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


def provision_reviews_for_staging_revision(revision: StagingBatchRevision) -> list[StagingReview]:
    """
    Provisions reviews for a StagingBatchRevision based on ReviewConfig if no reviews exist.
    While a revision is in draft mode, no review records are created.
    Existing reviews are never re-provisioned.
    Evaluates scopes against changed files and supports decision inheritance.
    """
    from reviews.models import ReviewConfig
    configs = ReviewConfig.objects.filter(project=revision.staging_batch.project, type="staging").select_related("scope")
    batch = revision.staging_batch
    prev_rev = (
        batch.revisions.filter(revision_number__lt=revision.revision_number)
        .order_by("-revision_number")
        .first()
    )
    return provision_reviews_for(
        revision,
        configs,
        review_model=StagingReview,
        revision_model=StagingBatchRevision,
        prev_rev=prev_rev,
    )


def mark_staging_ready_for_review(revision: StagingBatchRevision) -> None:
    """
    Transitions a StagingBatchRevision out of draft mode and provisions reviews.
    """
    mark_ready(revision, revision_model=StagingBatchRevision, provision_fn=provision_reviews_for_staging_revision)


def mark_staging_draft(revision: StagingBatchRevision) -> None:
    """
    Transitions a StagingBatchRevision into manual draft mode without debounce timer.
    Existing reviews are not modified or removed.
    """
    mark_draft(revision, revision_model=StagingBatchRevision)


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


def get_staging_review(batch: StagingBatch, reviewer_str: str | None) -> StagingReview:
    """Gets or creates the StagingReview on the batch's latest revision."""
    latest_rev = batch.latest_revision
    if not latest_rev:
        raise ValueError(f"Staging batch #{batch.id} has no revisions.")
    return get_or_create_review(latest_rev, reviewer_str, StagingReview)


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


def validate_staging_merge(batch: StagingBatch) -> list[str]:
    """
    Returns all blocking reasons for merging this staging batch; an empty list means it may be merged.
    """
    errors = []

    if batch.state == StagingBatch.State.MERGED:
        errors.append(f"Staging batch #{batch.id} is already merged.")

    latest_rev = batch.latest_revision
    if not latest_rev:
        errors.append(f"Staging batch #{batch.id} has no revisions.")
        return errors

    if latest_rev.is_draft:
        errors.append(f"Staging batch #{batch.id} is currently in draft mode and cannot be merged.")

    unapproved = latest_rev.reviews.exclude(state__in=[StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN])
    if unapproved.exists():
        unapproved_names = [str(r.reviewer_user or r.reviewer_group or r.dynamic_role) for r in unapproved]
        errors.append(
            f"Staging batch #{batch.id} cannot be merged because the following reviews are not approved: {', '.join(unapproved_names)}."
        )

    for pr in batch_member_prs(batch):
        if pr.is_draft:
            errors.append(f"Pull request #{pr.number} in batch is in draft mode.")
        if pr.is_mergeable is False:
            errors.append(f"Pull request #{pr.number} in batch has merge conflicts.")

    return errors


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


def execute_staging_merge(batch: StagingBatch) -> None:
    """
    Merges all non-merged member PRs of the batch on the forge via execute_pr_merge,
    then closes the batch (state=MERGED, closed_at). Callers must validate via
    validate_staging_merge first; this function locks the batch.
    Raises ValueError on forge failure (contract unchanged until P1).
    """
    locked = StagingBatch.objects.select_for_update().get(pk=batch.pk)
    for pr in batch_member_prs(locked):
        if pr.state != PullRequest.State.MERGED:
            execute_pr_merge(pr)

    locked.state = StagingBatch.State.MERGED
    locked.closed_at = timezone.now()
    locked.save(update_fields=["state", "closed_at"])
    batch.state = locked.state
    batch.closed_at = locked.closed_at


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

            reasons = validate_staging_merge(batch)
            if reasons:
                errors.extend(reasons)
                continue

            batches_to_merge.append(batch)

        if errors:
            return [], errors

        # 2. Execution pass: all batches validated, now perform atomic merges
        updated_batches = []
        for batch in batches_to_merge:
            try:
                execute_staging_merge(batch)
            except ValueError as e:
                return [], [str(e)]

            updated_batches.append(batch_to_detail(batch))

        return updated_batches, []
