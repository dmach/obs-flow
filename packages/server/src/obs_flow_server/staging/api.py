import msgspec
from asgiref.sync import sync_to_async
from django.http import HttpResponseBadRequest

from obs_flow_common.messages import (
    StagingCreateRequest,
    StagingEditRequest,
    StagingReadyForReviewRequest,
    StagingReadyForReviewResponse,
    StagingConvertToDraftRequest,
    StagingConvertToDraftResponse,
    StagingMergeRequest,
    StagingMergeResponse,
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
)
from obs_flow_server.api import api

from accounts.helpers import get_authenticated_user
from core.models import Project
from reviews.workflows import apply_review_action, clear_needinfo, parse_reviewer, review_to_detail
from staging.models import StagingBatch, StagingReview
from staging.workflows import (
    add_prs_to_batch,
    batch_to_detail,
    create_batch,
    get_staging_review,
    mark_staging_draft,
    mark_staging_ready_for_review,
    merge_batches,
    remove_prs_from_batch,
    update_batch,
)


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

        detail = create_batch(
            project=project,
            title=payload.title,
            author=user,
            embargo_date=payload.embargo_date,
            release_date=payload.release_date,
        )
        return msgspec.structs.asdict(detail)
    return await sync_to_async(do_create)()


@api.post("/api/v1/staging/edit")
@sync_to_async
def edit_staging_endpoint(payload: StagingEditRequest):
    batch = update_batch(
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

    try:
        prs = add_prs_to_batch(batch, payload.pull_request_ids)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))

    res = StagingAddResponse(id=batch.id, pull_requests=prs)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/remove")
@sync_to_async
def remove_from_staging_endpoint(payload: StagingRemoveRequest):
    batch = StagingBatch.objects.get(id=payload.id)

    prs = remove_prs_from_batch(batch, payload.pull_request_ids)

    res = StagingRemoveResponse(id=batch.id, pull_requests=prs)
    return msgspec.structs.asdict(res)


# =====================================================================
# Staging Review Endpoints
# =====================================================================


@api.post("/api/v1/staging_review/show")
@sync_to_async
def show_staging_review_endpoint(payload: StagingReviewShowRequest):
    batch = StagingBatch.objects.get(id=payload.staging_id)
    latest_rev = batch.latest_revision
    if not latest_rev:
        res = StagingReviewShowResponse(staging_id=payload.staging_id, reviews=[])
        return msgspec.structs.asdict(res)

    reviews = latest_rev.reviews.select_related("scope", "actor", "reviewer_user", "reviewer_group").all()

    if payload.reviewer:
        user, group, role = parse_reviewer(payload.reviewer)
        if user:
            reviews = reviews.filter(reviewer_user=user)
        elif group:
            reviews = reviews.filter(reviewer_group=group)
        elif role:
            reviews = reviews.filter(dynamic_role=role)

    details = [review_to_detail(r) for r in reviews]
    res = StagingReviewShowResponse(staging_id=payload.staging_id, reviews=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/approve")
@sync_to_async
def approve_staging_review_endpoint(payload: StagingReviewApproveRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    user = get_authenticated_user(request)
    review = get_staging_review(batch, payload.reviewer)
    apply_review_action(review, StagingReview.State.ACCEPTED, user, None)

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/decline")
@sync_to_async
def decline_staging_review_endpoint(payload: StagingReviewDeclineRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    user = get_authenticated_user(request)
    review = get_staging_review(batch, payload.reviewer)
    apply_review_action(review, StagingReview.State.REJECTED, user, payload.message)

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/needinfo")
@sync_to_async
def needinfo_staging_review_endpoint(payload: StagingReviewNeedInfoRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    user = get_authenticated_user(request)
    review = get_staging_review(batch, payload.reviewer)
    apply_review_action(review, StagingReview.State.NEEDINFO, user, payload.message)

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/clear_needinfo")
@sync_to_async
def clear_needinfo_staging_review_endpoint(payload: StagingReviewClearNeedInfoRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)
    latest_rev = batch.latest_revision
    if not latest_rev:
        raise ValueError(f"Staging batch #{batch.id} has no revisions.")

    user = get_authenticated_user(request)
    cleared = clear_needinfo(latest_rev, user, payload.message, StagingReview, payload.reviewer)

    res = StagingReviewShowResponse(
        staging_id=payload.staging_id,
        reviews=[review_to_detail(r) for r in cleared],
    )
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging_review/reopen")
@sync_to_async
def reopen_staging_review_endpoint(payload: StagingReviewReopenRequest, request):
    batch = StagingBatch.objects.get(id=payload.staging_id)

    user = get_authenticated_user(request)
    review = get_staging_review(batch, payload.reviewer)
    apply_review_action(review, StagingReview.State.PENDING, user, payload.message)

    res = StagingReviewActionResponse(staging_id=payload.staging_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/ready-for-review")
@sync_to_async
def staging_ready_for_review_endpoint(payload: StagingReadyForReviewRequest):
    updated_batches = []
    for batch_id in payload.staging_ids:
        try:
            batch = StagingBatch.objects.get(id=batch_id)
        except StagingBatch.DoesNotExist:
            return HttpResponseBadRequest(f"Staging batch #{batch_id} does not exist.")

        latest_rev = batch.latest_revision
        if not latest_rev:
            return HttpResponseBadRequest(f"Staging batch #{batch_id} has no revisions.")

        mark_staging_ready_for_review(latest_rev)
        batch.refresh_from_db()
        updated_batches.append(batch_to_detail(batch))

    res = StagingReadyForReviewResponse(staging_batches=updated_batches)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/convert-to-draft")
@sync_to_async
def staging_convert_to_draft_endpoint(payload: StagingConvertToDraftRequest):
    updated_batches = []
    for batch_id in payload.staging_ids:
        try:
            batch = StagingBatch.objects.get(id=batch_id)
        except StagingBatch.DoesNotExist:
            return HttpResponseBadRequest(f"Staging batch #{batch_id} does not exist.")

        latest_rev = batch.latest_revision
        if not latest_rev:
            return HttpResponseBadRequest(f"Staging batch #{batch_id} has no revisions.")

        mark_staging_draft(latest_rev)
        batch.refresh_from_db()
        updated_batches.append(batch_to_detail(batch))

    res = StagingConvertToDraftResponse(staging_batches=updated_batches)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/staging/merge")
@sync_to_async
def staging_merge_endpoint(payload: StagingMergeRequest):
    if not payload.staging_ids:
        return HttpResponseBadRequest("No staging batch IDs provided.")

    updated_batches, errors = merge_batches(payload.staging_ids)
    if errors:
        return HttpResponseBadRequest("\n".join(errors))

    res = StagingMergeResponse(staging_batches=updated_batches)
    return msgspec.structs.asdict(res)
