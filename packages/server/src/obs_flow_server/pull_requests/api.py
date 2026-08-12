import re

import msgspec
from asgiref.sync import sync_to_async
from django.utils import timezone
from django_bolt import BoltAPI

from obs_flow_common.messages import (
    PRDetail,
    PRSyncRequest,
    PRSyncResponse,
    PRReviewShowRequest,
    PRReviewShowResponse,
    PRReviewActionResponse,
    PRReviewApproveRequest,
    PRReviewDeclineRequest,
    PRReviewNeedInfoRequest,
    PRReviewClearNeedInfoRequest,
    PRReviewReopenRequest,
    ReviewDetail,
)
from obs_flow_server.api import api

from accounts.models import User, Group
from core.models import GitMapping, Project
from pull_requests.models import PullRequest, PullRequestRevision, PullRequestReview


PR_ID_REGEX = re.compile(r"^([^/]+)/([^#]+)#(\d+)$")


def get_pull_request(pull_request_id: str) -> PullRequest:
    match = PR_ID_REGEX.match(pull_request_id)
    if not match:
        raise ValueError(f"Invalid pull request ID format: {pull_request_id}")
    owner, repo, number = match.groups()
    number = int(number)

    return PullRequest.objects.get(
        target__owner=owner,
        target__repo=repo,
        number=number,
    )


def parse_reviewer(reviewer_str: str | None):
    if not reviewer_str:
        # Default to admin user
        admin_user = User.objects.get(username="admin")
        return admin_user, None

    if reviewer_str.startswith("@"):
        group_name = reviewer_str[1:]
        group = Group.objects.get(name=group_name)
        return None, group
    else:
        user = User.objects.get(username=reviewer_str)
        return user, None


def review_to_detail(review: PullRequestReview) -> ReviewDetail:
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


def get_review_for_request(revision: PullRequestRevision, reviewer_str: str | None) -> PullRequestReview:
    user, group = parse_reviewer(reviewer_str)
    if user:
        review, _ = PullRequestReview.objects.get_or_create(
            revision=revision, reviewer_user=user, defaults={"state": PullRequestReview.State.PENDING}
        )
    else:
        review, _ = PullRequestReview.objects.get_or_create(
            revision=revision, reviewer_group=group, defaults={"state": PullRequestReview.State.PENDING}
        )
    return review


@api.post("/api/v1/pr_review/show")
@sync_to_async
def show_review_endpoint(req: PRReviewShowRequest):
    pr = get_pull_request(req.pull_request_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()

    reviews = latest_revision.reviews.all()
    if req.reviewer:
        user, group = parse_reviewer(req.reviewer)
        if user:
            reviews = reviews.filter(reviewer_user=user)
        elif group:
            reviews = reviews.filter(reviewer_group=group)

    details = [review_to_detail(r) for r in reviews]
    res = PRReviewShowResponse(pull_request_id=req.pull_request_id, reviews=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/approve")
@sync_to_async
def approve_review_endpoint(req: PRReviewApproveRequest):
    pr = get_pull_request(req.pull_request_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()

    review = get_review_for_request(latest_revision, req.reviewer)
    review.state = PullRequestReview.State.ACCEPTED
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = None
    review.save()

    res = PRReviewActionResponse(pull_request_id=req.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/decline")
@sync_to_async
def decline_review_endpoint(req: PRReviewDeclineRequest):
    pr = get_pull_request(req.pull_request_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()

    review = get_review_for_request(latest_revision, req.reviewer)
    review.state = PullRequestReview.State.REJECTED
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = req.message
    review.save()

    res = PRReviewActionResponse(pull_request_id=req.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/needinfo")
@sync_to_async
def needinfo_review_endpoint(req: PRReviewNeedInfoRequest):
    pr = get_pull_request(req.pull_request_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()

    review = get_review_for_request(latest_revision, req.reviewer)
    review.state = PullRequestReview.State.NEEDINFO
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = req.message
    review.save()

    res = PRReviewActionResponse(pull_request_id=req.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/clear_needinfo")
@sync_to_async
def clear_needinfo_review_endpoint(req: PRReviewClearNeedInfoRequest):
    pr = get_pull_request(req.pull_request_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()

    # Clear needinfo on all reviews for this revision that are in NEEDINFO state
    reviews = latest_revision.reviews.filter(state=PullRequestReview.State.NEEDINFO)
    admin_user = User.objects.get(username="admin")

    last_review = None
    for review in reviews:
        review.state = PullRequestReview.State.PENDING
        review.actor = admin_user
        review.justification = req.message
        review.save()
        last_review = review

    if not last_review:
        # If no reviews were in NEEDINFO, just get/create a default one to return
        last_review = get_review_for_request(latest_revision, None)

    res = PRReviewActionResponse(pull_request_id=req.pull_request_id, review=review_to_detail(last_review))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/reopen")
@sync_to_async
def reopen_review_endpoint(req: PRReviewReopenRequest):
    pr = get_pull_request(req.pull_request_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()

    review = get_review_for_request(latest_revision, req.reviewer)
    review.state = PullRequestReview.State.PENDING
    admin_user = User.objects.get(username="admin")
    review.actor = admin_user
    review.justification = req.message
    review.save()

    res = PRReviewActionResponse(pull_request_id=req.pull_request_id, review=review_to_detail(review))
    return msgspec.structs.asdict(res)


import urllib.request
import urllib.error
import json
from django.conf import settings
from django.http import HttpResponseServerError


def _do_sync_pull_request(req: PRSyncRequest) -> PRSyncResponse:
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

    # Get or create Project and GitMapping
    project_name = f"{req.owner}:{req.repo}"
    project, _ = Project.objects.get_or_create(name=project_name)
    git_mapping, _ = GitMapping.objects.get_or_create(
        owner=req.owner, repo=req.repo, branch="main", defaults={"project": project}
    )

    # Get or create PR
    pr, created = PullRequest.objects.get_or_create(
        target=git_mapping,
        number=req.number,
        defaults={
            "author": author,
            "title": title,
            "is_draft": draft,
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
        pr.is_draft = draft
        pr.is_mergeable = mergeable
        pr.state = pr_state
        pr.save()

    # Check revisions
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if not latest_revision or latest_revision.head_sha != head_sha:
        rev_number = (latest_revision.revision_number + 1) if latest_revision else 1
        latest_revision = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=rev_number,
            head_sha=head_sha,
            base_sha=base_sha
        )

    return PRSyncResponse(
        pull_request=PRDetail(
            id=f"{req.owner}/{req.repo}#{req.number}",
            title=pr.title,
            state=pr.state,
            is_draft=pr.is_draft,
            is_mergeable=pr.is_mergeable,
            author=pr.author.username,
            latest_revision=latest_revision.revision_number,
            head_sha=latest_revision.head_sha,
            base_sha=latest_revision.base_sha,
        )
    )


@api.post("/api/v1/pr/sync")
async def sync_pull_request_endpoint(payload: PRSyncRequest):
    if not getattr(settings, "GITEA_URL", None) or not getattr(settings, "GITEA_TOKEN", None):
        return HttpResponseServerError("GITEA_URL and GITEA_TOKEN must be configured.")

    try:
        res = await sync_to_async(_do_sync_pull_request)(payload)
    except Exception as e:
        return HttpResponseServerError(str(e))

    return msgspec.structs.asdict(res)
