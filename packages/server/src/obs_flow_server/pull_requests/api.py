from datetime import timedelta

import msgspec
from accounts.helpers import build_user_dto, get_authenticated_user
from accounts.models import User
from asgiref.sync import sync_to_async
from core.models import Package, Project
from django.conf import settings
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.utils import timezone
from obs_flow_common.messages import (
    PRConvertToDraftRequest,
    PRConvertToDraftResponse,
    PRCreateRequest,
    PRCreateResponse,
    PRDetail,
    PRMergeRequest,
    PRMergeResponse,
    PRReadyForReviewRequest,
    PRReadyForReviewResponse,
    PRReviewActionResponse,
    PRReviewApproveRequest,
    PRReviewClearNeedInfoRequest,
    PRReviewDeclineRequest,
    PRReviewNeedInfoRequest,
    PRReviewReopenRequest,
    PRReviewShowRequest,
    PRReviewShowResponse,
    PRSyncRequest,
)
from obs_flow_server.api import api
from reviews.workflows import (
    apply_review_action,
    clear_needinfo,
    get_or_create_review,
    parse_reviewer,
    review_to_detail,
)

from pull_requests.models import PullRequest, PullRequestReview, PullRequestRevision
from pull_requests.workflows import (
    mark_draft,
    mark_ready_for_review,
    merge_pull_requests,
    pr_to_detail,
    provision_reviews_for_revision,
    sync_pull_request,
)


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
    cleared = clear_needinfo(pr.latest_revision, user, payload.message, PullRequestReview, payload.reviewer)

    res = PRReviewShowResponse(
        pull_request_id=payload.pull_request_id,
        reviews=[review_to_detail(r) for r in cleared],
    )
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


def build_pr_detail(pr: PullRequest) -> PRDetail:
    latest_revision = pr.revisions.order_by("-revision_number").first()
    return PRDetail(
        id=pr.formatted_id,
        title=pr.title,
        state=pr.state,
        is_draft=pr.is_draft,
        is_mergeable=pr.is_mergeable,
        author=build_user_dto(pr.author),
        latest_revision=latest_revision.revision_number if latest_revision else 1,
        head_sha=latest_revision.head_sha if latest_revision else "",
        base_sha=latest_revision.base_sha if latest_revision else "",
    )


@api.post("/api/v1/pr/create")
@sync_to_async
@transaction.atomic
def create_pull_request_endpoint(payload: PRCreateRequest):
    try:
        target_project = Project.objects.get(name=payload.target_project)
    except Project.DoesNotExist:
        raise ValueError(f"Target project '{payload.target_project}' does not exist")

    target_package = None
    if payload.target_package:
        try:
            target_package = Package.objects.get(project=target_project, name=payload.target_package)
        except Package.DoesNotExist:
            raise ValueError(
                f"Target package '{payload.target_package}' does not exist in project '{payload.target_project}'"
            )

    author, _ = User.objects.get_or_create(
        username=payload.author,
        defaults={"username_lower": payload.author.lower(), "account_type": User.AccountType.HUMAN},
    )

    from django.db.models import Max

    max_num = (
        PullRequest.objects.filter(project=target_project, package=target_package).aggregate(Max("number"))[
            "number__max"
        ]
        or 0
    )
    pr_number = max_num + 1

    pr = PullRequest.objects.create(
        project=target_project,
        package=target_package,
        number=pr_number,
        author=author,
        title=payload.title,
        source_owner=payload.source_owner,
        source_repo=payload.source_repo,
        source_branch=payload.source_branch,
        state=PullRequest.State.OPEN,
    )

    timeout_minutes = target_project.effective_review_debounce_minutes
    if payload.is_draft:
        rev_is_draft = True
        rev_draft_expires_at = None
    elif timeout_minutes == 0:
        rev_is_draft = False
        rev_draft_expires_at = None
    else:
        rev_is_draft = True
        rev_draft_expires_at = timezone.now() + timedelta(minutes=timeout_minutes)

    target_branch = target_project.branch_name or "main"
    from pull_requests.fingerprint import PRRevisionPayload
    pr_payload = PRRevisionPayload(
        head_sha=payload.head_sha or "0" * 40,
        base_sha=payload.base_sha or "0" * 40,
        target_branch=target_branch,
    )
    computed_fingerprint = pr_payload.compute_fingerprint()

    rev = PullRequestRevision.objects.create(
        pull_request=pr,
        revision_number=1,
        head_sha=payload.head_sha or "0" * 40,
        base_sha=payload.base_sha or "0" * 40,
        fingerprint=computed_fingerprint,
        is_draft=rev_is_draft,
        draft_expires_at=rev_draft_expires_at,
    )

    if not rev.is_draft:
        provision_reviews_for_revision(rev)

    res = PRCreateResponse(pull_request=build_pr_detail(pr))
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
