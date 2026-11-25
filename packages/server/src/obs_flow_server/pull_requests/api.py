import msgspec
from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseServerError

from obs_flow_common.messages import (
    PRSyncRequest,
    PRReadyForReviewRequest,
    PRReadyForReviewResponse,
    PRConvertToDraftRequest,
    PRConvertToDraftResponse,
    PRMergeRequest,
    PRMergeResponse,
    PRReviewShowRequest,
    PRReviewShowResponse,
    PRReviewActionResponse,
    PRReviewApproveRequest,
    PRReviewDeclineRequest,
    PRReviewNeedInfoRequest,
    PRReviewClearNeedInfoRequest,
    PRReviewReopenRequest,
)
from obs_flow_server.api import api

from accounts.helpers import get_authenticated_user
from pull_requests.models import PullRequest, PullRequestReview
from pull_requests.workflows import (
    mark_draft,
    mark_ready_for_review,
    merge_pull_requests,
    pr_to_detail,
    sync_pull_request,
)
from reviews.workflows import apply_review_action, clear_needinfo, get_or_create_review, parse_reviewer, review_to_detail


@api.post("/api/v1/pr_review/show")
@sync_to_async
def show_review_endpoint(payload: PRReviewShowRequest):
    pr = PullRequest.objects.get_by_text_id(payload.pull_request_id)
    latest_revision = pr.latest_revision

    reviews = latest_revision.reviews.select_related("scope", "actor", "reviewer_user", "reviewer_group").all()
    if payload.reviewer:
        user, group, role = parse_reviewer(payload.reviewer)
        if user:
            reviews = reviews.filter(reviewer_user=user)
        elif group:
            reviews = reviews.filter(reviewer_group=group)
        elif role:
            reviews = reviews.filter(dynamic_role=role)

    details = [review_to_detail(r) for r in reviews]
    res = PRReviewShowResponse(pull_request_id=payload.pull_request_id, reviews=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/approve")
@sync_to_async
def approve_review_endpoint(payload: PRReviewApproveRequest, request):
    pr = PullRequest.objects.get_by_text_id(payload.pull_request_id)
    latest_revision = pr.latest_revision

    user = get_authenticated_user(request)
    review = get_or_create_review(latest_revision, payload.reviewer, PullRequestReview)
    apply_review_action(review, PullRequestReview.State.ACCEPTED, user, None)

    res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/decline")
@sync_to_async
def decline_review_endpoint(payload: PRReviewDeclineRequest, request):
    pr = PullRequest.objects.get_by_text_id(payload.pull_request_id)
    latest_revision = pr.latest_revision

    user = get_authenticated_user(request)
    review = get_or_create_review(latest_revision, payload.reviewer, PullRequestReview)
    apply_review_action(review, PullRequestReview.State.REJECTED, user, payload.message)

    res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/needinfo")
@sync_to_async
def needinfo_review_endpoint(payload: PRReviewNeedInfoRequest, request):
    pr = PullRequest.objects.get_by_text_id(payload.pull_request_id)
    latest_revision = pr.latest_revision

    user = get_authenticated_user(request)
    review = get_or_create_review(latest_revision, payload.reviewer, PullRequestReview)
    apply_review_action(review, PullRequestReview.State.NEEDINFO, user, payload.message)

    res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/clear_needinfo")
@sync_to_async
def clear_needinfo_review_endpoint(payload: PRReviewClearNeedInfoRequest, request):
    pr = PullRequest.objects.get_by_text_id(payload.pull_request_id)

    user = get_authenticated_user(request)
    last_review = clear_needinfo(pr.latest_revision, user, payload.message, PullRequestReview, payload.reviewer)

    res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(last_review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/reopen")
@sync_to_async
def reopen_review_endpoint(payload: PRReviewReopenRequest, request):
    pr = PullRequest.objects.get_by_text_id(payload.pull_request_id)
    latest_revision = pr.latest_revision

    user = get_authenticated_user(request)
    review = get_or_create_review(latest_revision, payload.reviewer, PullRequestReview)
    apply_review_action(review, PullRequestReview.State.PENDING, user, payload.message)

    res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr/sync")
async def sync_pull_request_endpoint(payload: PRSyncRequest):
    if not getattr(settings, "GITEA_URL", None) or not getattr(settings, "GITEA_TOKEN", None):
        return HttpResponseServerError("GITEA_URL and GITEA_TOKEN must be configured.")

    try:
        res = await sync_to_async(sync_pull_request)(payload)
    except Exception as e:
        return HttpResponseServerError(str(e))

    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr/ready-for-review")
@sync_to_async
def pr_ready_for_review_endpoint(payload: PRReadyForReviewRequest):
    updated_prs = []
    for pr_id in payload.pull_request_ids:
        try:
            pr = PullRequest.objects.get_by_text_id(pr_id)
        except (PullRequest.DoesNotExist, ValueError) as e:
            return HttpResponseBadRequest(str(e))

        latest_revision = pr.latest_revision
        if not latest_revision:
            return HttpResponseBadRequest(f"Pull request {pr_id} has no revisions.")

        mark_ready_for_review(latest_revision)
        pr.refresh_from_db()
        latest_revision.refresh_from_db()
        updated_prs.append(pr_to_detail(pr, latest_revision))

    res = PRReadyForReviewResponse(pull_requests=updated_prs)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr/convert-to-draft")
@sync_to_async
def pr_convert_to_draft_endpoint(payload: PRConvertToDraftRequest):
    updated_prs = []
    for pr_id in payload.pull_request_ids:
        try:
            pr = PullRequest.objects.get_by_text_id(pr_id)
        except (PullRequest.DoesNotExist, ValueError) as e:
            return HttpResponseBadRequest(str(e))

        latest_revision = pr.latest_revision
        if not latest_revision:
            return HttpResponseBadRequest(f"Pull request {pr_id} has no revisions.")

        mark_draft(latest_revision)
        pr.refresh_from_db()
        latest_revision.refresh_from_db()
        updated_prs.append(pr_to_detail(pr, latest_revision))

    res = PRConvertToDraftResponse(pull_requests=updated_prs)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr/merge")
@sync_to_async
def pr_merge_endpoint(payload: PRMergeRequest):
    if not payload.pull_request_ids:
        return HttpResponseBadRequest("No pull request IDs provided.")

    updated_prs, errors = merge_pull_requests(payload.pull_request_ids)
    if errors:
        return HttpResponseBadRequest("\n".join(errors))

    res = PRMergeResponse(pull_requests=updated_prs)
    return msgspec.structs.asdict(res)
