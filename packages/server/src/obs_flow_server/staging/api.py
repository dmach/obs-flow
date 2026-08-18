import msgspec
from asgiref.sync import sync_to_async
from django.utils import timezone
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

from accounts.models import User, Group
from core.models import Project
from pull_requests.models import PullRequest
from pull_requests.api import get_pull_request, parse_reviewer
from staging.models import StagingBatch, StagingBatchPullRequest, StagingReview
from staging.views import update_staging_batch


def pr_to_id(pr: PullRequest) -> str:
    return f"{pr.target.owner}/{pr.target.repo}#{pr.number}"


def batch_to_detail(batch: StagingBatch) -> StagingDetail:
    prs = [pr_to_id(bpr.pull_request) for bpr in batch.batch_pull_requests.all()]
    return StagingDetail(
        id=batch.id,
        state=batch.state,
        creator=batch.author.username if batch.author else None,
        title=batch.title,
        target_project=batch.project.name,
        pull_requests=prs,
        embargo_date=batch.embargo_date.isoformat() if batch.embargo_date else None,
        release_date=batch.release_date.isoformat() if batch.release_date else None,
    )


def review_to_detail(review: StagingReview) -> ReviewDetail:
    if review.reviewer_user:
        reviewer = review.reviewer_user.username
    elif review.reviewer_group:
        reviewer = f"@{review.reviewer_group.name}"
    else:
        reviewer = f"role:{review.dynamic_role}"

    return ReviewDetail(
        reviewer=reviewer,
        state=review.state,
        actor=review.actor.username if review.actor else None,
        when=review.updated_at.isoformat(),
        why=review.justification,
    )


def get_review_for_request(batch: StagingBatch, reviewer_str: str | None) -> StagingReview:
    user, group = parse_reviewer(reviewer_str)
    if user:
        review, _ = StagingReview.objects.get_or_create(
            staging=batch, reviewer_user=user, defaults={"state": StagingReview.State.PENDING}
        )
    else:
        review, _ = StagingReview.objects.get_or_create(
            staging=batch, reviewer_group=group, defaults={"state": StagingReview.State.PENDING}
        )
    return review


@api.post("/api/v1/staging/show/{staging_id}")
@sync_to_async
def show_staging_endpoint(request, staging_id: int):
    batch = StagingBatch.objects.get(id=staging_id)
    detail = batch_to_detail(batch)
    return msgspec.structs.asdict(detail)


@api.post("/api/v1/staging/create")
@sync_to_async
def create_staging_endpoint(payload: StagingCreateRequest):
    project = Project.objects.get(name=payload.project)
    admin_user = User.objects.get(username="admin")

    batch = StagingBatch.objects.create(
        project=project,
        title=payload.title,
        author=admin_user,
        embargo_date=timezone.datetime.fromisoformat(payload.embargo_date) if payload.embargo_date else None,
        release_date=timezone.datetime.fromisoformat(payload.release_date) if payload.release_date else None,
    )

    # Create default reviews for the staging batch
    StagingReview.objects.create(
        staging=batch,
        reviewer_user=admin_user,
        state=StagingReview.State.PENDING,
    )

    res = StagingCreateResponse(
        id=batch.id,
        state=batch.state,
        creator=batch.author.username if batch.author else None,
        title=batch.title,
        target_project=batch.project.name,
        pull_requests=[],
        embargo_date=batch.embargo_date.isoformat() if batch.embargo_date else None,
        release_date=batch.release_date.isoformat() if batch.release_date else None,
    )
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/edit")
@sync_to_async
def edit_staging_endpoint(payload: StagingEditRequest):
    batch = update_staging_batch(
        batch_id=payload.id,
        title=payload.title,
        embargo_date=payload.embargo_date,
        release_date=payload.release_date,
    )

    res = StagingEditResponse(
        id=batch.id,
        state=batch.state,
        creator=batch.author.username if batch.author else None,
        title=batch.title,
        target_project=batch.project.name,
        pull_requests=[pr_to_id(bpr.pull_request) for bpr in batch.batch_pull_requests.all()],
        embargo_date=batch.embargo_date.isoformat() if batch.embargo_date else None,
        release_date=batch.release_date.isoformat() if batch.release_date else None,
    )
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/add")
@sync_to_async
def add_to_staging_endpoint(payload: StagingAddRequest):
    batch = StagingBatch.objects.get(id=payload.id)

    for pr_id in payload.pull_request_ids:
        pr = get_pull_request(pr_id)
        StagingBatchPullRequest.objects.get_or_create(staging_batch=batch, pull_request=pr)

    prs = [pr_to_id(bpr.pull_request) for bpr in batch.batch_pull_requests.all()]
    res = StagingAddResponse(id=batch.id, pull_requests=prs)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/remove")
@sync_to_async
def remove_from_staging_endpoint(payload: StagingRemoveRequest):
    batch = StagingBatch.objects.get(id=payload.id)

    for pr_id in payload.pull_request_ids:
        try:
            pr = get_pull_request(pr_id)
            StagingBatchPullRequest.objects.filter(staging_batch=batch, pull_request=pr).delete()
        except Exception:
            pass

    prs = [pr_to_id(bpr.pull_request) for bpr in batch.batch_pull_requests.all()]
    res = StagingRemoveResponse(id=batch.id, pull_requests=prs)
    return msgspec.structs.asdict(res)


# =====================================================================
# Staging Review Endpoints
# =====================================================================


@api.post("/api/v1/staging_review/show")
@sync_to_async
def show_staging_review_endpoint(payload: StagingReviewShowRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    reviews = batch.reviews.all()

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
def approve_staging_review_endpoint(payload: StagingReviewApproveRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.ACCEPTED
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = None
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/decline")
@sync_to_async
def decline_staging_review_endpoint(payload: StagingReviewDeclineRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.REJECTED
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = payload.message
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/needinfo")
@sync_to_async
def needinfo_staging_review_endpoint(payload: StagingReviewNeedInfoRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.NEEDINFO
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = payload.message
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/clear_needinfo")
@sync_to_async
def clear_needinfo_staging_review_endpoint(payload: StagingReviewClearNeedInfoRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    # Clear needinfo on all reviews for this batch that are in NEEDINFO state
    reviews = batch.reviews.filter(state=StagingReview.State.NEEDINFO)
    admin_user = User.objects.get(username="admin")

    last_review = None
    for review in reviews:
        review.state = StagingReview.State.PENDING
        review.actor = admin_user
        review.justification = payload.message
        review.save()
        last_review = review

    if not last_review:
        last_review = get_review_for_request(batch, None)

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(last_review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/reopen")
@sync_to_async
def reopen_staging_review_endpoint(payload: StagingReviewReopenRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    review = get_review_for_request(batch, payload.reviewer)
    review.state = StagingReview.State.PENDING
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = payload.message
    review.save()

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)
