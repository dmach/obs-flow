from datetime import timedelta
import msgspec
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponseBadRequest
from django_bolt import BoltAPI

from obs_flow_common.messages import (
    StagingDetail,
    StagingCreateRequest,
    StagingCreateResponse,
    StagingEditRequest,
    StagingEditResponse,
    StagingAddRequest,
    StagingAddResponse,
    StagingRemoveRequest,
    StagingRemoveResponse,
    StagingReviewShowRequest,
    StagingReviewShowResponse,
    StagingReviewActionResponse,
    StagingReviewApproveRequest,
    StagingReviewDeclineRequest,
    StagingReviewNeedInfoRequest,
    StagingReviewClearNeedInfoRequest,
    StagingReviewReopenRequest,
    ReviewDetail,
)
from obs_flow_server.api import api

import hashlib
from accounts.helpers import build_user_dto, get_authenticated_user, get_auth_header
from accounts.models import User, Group
from core.models import Project
from pull_requests.models import PullRequest
from pull_requests.api import get_pull_request, parse_reviewer
from reviews.api import build_reviewer_dto_from_fields
from staging.models import StagingBatch, StagingBatchRevision, StagingBatchRevisionPullRequest, StagingReview
from staging.views import update_staging_batch


def pr_to_id(pr: PullRequest) -> str:
    return f"{pr.target.owner}/{pr.target.repo}#{pr.number}"


def compute_staging_fingerprint(batch: StagingBatch, pr_revisions) -> str:
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
    fingerprint = compute_staging_fingerprint(batch, pr_revisions)
    latest_rev = batch.revisions.order_by("-revision_number").first()

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
    """
    rev = StagingBatchRevision.objects.select_for_update().get(pk=revision.pk)
    if rev.is_draft:
        return []
    if rev.reviews.exists():
        return list(rev.reviews.all())

    from reviews.models import ReviewConfig
    configs = ReviewConfig.objects.filter(project=rev.staging_batch.project, type="staging")
    created_reviews = []
    if configs.exists():
        config_to_review = {}
        for config in configs:
            review = StagingReview.objects.create(
                revision=rev,
                reviewer_user=config.reviewer_user,
                reviewer_group=config.reviewer_group,
                dynamic_role=config.dynamic_role,
                state=StagingReview.State.PENDING,
            )
            config_to_review[config] = review
            created_reviews.append(review)

        # Set up dependencies between the created reviews
        for config, review in config_to_review.items():
            for dep_config in config.depends_on.all():
                if dep_config in config_to_review:
                    review.depends_on.add(config_to_review[dep_config])

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


def batch_to_detail(batch: StagingBatch) -> StagingDetail:
    latest_rev = batch.revisions.order_by("-revision_number").first()
    if latest_rev:
        prs = [
            pr_to_id(bpr.pull_request_revision.pull_request)
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
    )


def review_to_detail(review: StagingReview) -> ReviewDetail:
    reviewer_dto = build_reviewer_dto_from_fields(
        review.reviewer_user,
        review.reviewer_group,
        review.dynamic_role,
    )
    actor_dto = build_user_dto(review.actor) if review.actor else None

    return ReviewDetail(
        reviewer=reviewer_dto,
        state=review.state,
        actor=actor_dto,
        when=review.updated_at.isoformat(),
        why=review.justification,
    )


def get_review_for_request(batch: StagingBatch, reviewer_str: str | None) -> StagingReview:
    latest_rev = batch.revisions.order_by("-revision_number").first()
    if not latest_rev:
        raise ValueError(f"Staging batch #{batch.id} has no revisions.")
    user, group = parse_reviewer(reviewer_str)
    if user:
        review, _ = StagingReview.objects.get_or_create(
            revision=latest_rev, reviewer_user=user, defaults={"state": StagingReview.State.PENDING}
        )
    else:
        review, _ = StagingReview.objects.get_or_create(
            revision=latest_rev, reviewer_group=group, defaults={"state": StagingReview.State.PENDING}
        )
    return review


@api.post("/api/v1/staging/show/{staging_id}")
@sync_to_async
def show_staging_endpoint(request, staging_id: int):
    batch = StagingBatch.objects.get(id=staging_id)
    detail = batch_to_detail(batch)
    return msgspec.structs.asdict(detail)


@api.post("/api/v1/staging/create")
async def create_staging_endpoint(payload: StagingCreateRequest, request):
    def do_create():
        try:
            project = Project.objects.get(name=payload.project)
        except Project.DoesNotExist:
            return HttpResponseBadRequest(f"Project not found: {payload.project}")

        user = get_authenticated_user(request)

        batch = StagingBatch.objects.create(
            project=project,
            title=payload.title,
            author=user,
            embargo_date=timezone.datetime.fromisoformat(payload.embargo_date) if payload.embargo_date else None,
            release_date=timezone.datetime.fromisoformat(payload.release_date) if payload.release_date else None,
        )

        # Create revision 1 (empty)
        create_staging_revision(batch, [])

        detail = batch_to_detail(batch)
        return msgspec.structs.asdict(detail)
    return await sync_to_async(do_create)()


@api.post("/api/v1/staging/edit")
@sync_to_async
def edit_staging_endpoint(payload: StagingEditRequest):
    batch = update_staging_batch(
        batch_id=payload.id,
        title=payload.title,
        embargo_date=payload.embargo_date,
        release_date=payload.release_date,
    )

    detail = batch_to_detail(batch)
    return msgspec.structs.asdict(detail)


@api.post("/api/v1/staging/add")
@sync_to_async
def add_to_staging_endpoint(payload: StagingAddRequest):
    batch = StagingBatch.objects.get(id=payload.id)

    # Validate that all requested PRs target the same project as the batch
    resolved_prs = []
    for pr_id in payload.pull_request_ids:
        pr = get_pull_request(pr_id)
        if pr.target_project != batch.project:
            return HttpResponseBadRequest(
                f"Pull request '{pr_id}' belongs to project '{pr.target_project.name}', "
                f"which does not match staging batch project '{batch.project.name}'."
            )
        resolved_prs.append(pr)

    latest_rev = batch.revisions.order_by("-revision_number").first()
    current_prs = []
    if latest_rev:
        current_prs = [
            bpr.pull_request_revision.pull_request
            for bpr in latest_rev.revision_pull_requests.all()
        ]

    for pr in resolved_prs:
        if pr not in current_prs:
            current_prs.append(pr)

    pr_revisions = []
    for pr in current_prs:
        latest_pr_rev = pr.revisions.order_by("-revision_number").first()
        if latest_pr_rev:
            pr_revisions.append(latest_pr_rev)

    create_staging_revision(batch, pr_revisions)

    prs = [pr_to_id(pr) for pr in current_prs]
    res = StagingAddResponse(id=batch.id, pull_requests=prs)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/remove")
@sync_to_async
def remove_from_staging_endpoint(payload: StagingRemoveRequest):
    batch = StagingBatch.objects.get(id=payload.id)

    latest_rev = batch.revisions.order_by("-revision_number").first()
    current_prs = []
    if latest_rev:
        current_prs = [
            bpr.pull_request_revision.pull_request
            for bpr in latest_rev.revision_pull_requests.all()
        ]

    for pr_id in payload.pull_request_ids:
        try:
            pr = get_pull_request(pr_id)
            if pr in current_prs:
                current_prs.remove(pr)
        except Exception:
            pass

    pr_revisions = []
    for pr in current_prs:
        latest_pr_rev = pr.revisions.order_by("-revision_number").first()
        if latest_pr_rev:
            pr_revisions.append(latest_pr_rev)

    create_staging_revision(batch, pr_revisions)

    prs = [pr_to_id(pr) for pr in current_prs]
    res = StagingRemoveResponse(id=batch.id, pull_requests=prs)
    return msgspec.structs.asdict(res)


# =====================================================================
# Staging Review Endpoints
# =====================================================================


@api.post("/api/v1/staging_review/show")
@sync_to_async
def show_staging_review_endpoint(payload: StagingReviewShowRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)
    latest_rev = batch.revisions.order_by("-revision_number").first()
    if not latest_rev:
        res = StagingReviewShowResponse(staging_id=payload.staging_id, reviews=[])
        return msgspec.structs.asdict(res)

    reviews = latest_rev.reviews.all()

    if payload.reviewer:
        user, group = parse_reviewer(payload.reviewer)
        if user:
            reviews = reviews.filter(reviewer_user=user)
        elif group:
            reviews = reviews.filter(reviewer_group=group)

    details = [review_to_detail(r) for r in reviews]
    res = StagingReviewShowResponse(staging_id=payload.staging_id, reviews=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/approve")
@sync_to_async
def approve_staging_review_endpoint(payload: StagingReviewApproveRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.ACCEPTED
    user = get_authenticated_user(request)
    review.actor = user
    review.justification = None
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/decline")
@sync_to_async
def decline_staging_review_endpoint(payload: StagingReviewDeclineRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.REJECTED
    user = get_authenticated_user(request)
    review.actor = user
    review.justification = payload.message
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/needinfo")
@sync_to_async
def needinfo_staging_review_endpoint(payload: StagingReviewNeedInfoRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.NEEDINFO
    user = get_authenticated_user(request)
    review.actor = user
    review.justification = payload.message
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/clear_needinfo")
@sync_to_async
def clear_needinfo_staging_review_endpoint(payload: StagingReviewClearNeedInfoRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)
    latest_rev = batch.revisions.order_by("-revision_number").first()
    if not latest_rev:
        raise ValueError(f"Staging batch #{batch.id} has no revisions.")

    # Clear needinfo on all reviews for this batch revision that are in NEEDINFO state
    reviews = latest_rev.reviews.filter(state=StagingReview.State.NEEDINFO)
    user = get_authenticated_user(request)

    last_review = None
    for review in reviews:
        review.state = StagingReview.State.PENDING
        review.actor = user
        review.justification = payload.message
        review.save()
        last_review = review

    if not last_review:
        last_review = get_review_for_request(batch, None)

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(last_review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/reopen")
@sync_to_async
def reopen_staging_review_endpoint(payload: StagingReviewReopenRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.PENDING
    user = get_authenticated_user(request)
    review.actor = user
    review.justification = payload.message
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)
