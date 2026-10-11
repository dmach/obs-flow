from datetime import timedelta
import re

import msgspec
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from django_bolt import BoltAPI

from obs_flow_common.messages import (
    PRDetail,
    PRSyncRequest,
    PRSyncResponse,
    PRReadyForReviewRequest,
    PRReadyForReviewResponse,
    PRConvertToDraftRequest,
    PRConvertToDraftResponse,
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

from accounts.helpers import build_user_dto, get_authenticated_user, get_auth_header
from accounts.models import User, Group
from core.models import GitMapping, Project
from pull_requests.models import PullRequest, PullRequestRevision, PullRequestReview
from reviews.api import build_reviewer_dto_from_fields


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
def show_review_endpoint(payload: PRReviewShowRequest):
    pr = get_pull_request(payload.pull_request_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()

    reviews = latest_revision.reviews.all()
    if payload.reviewer:
        user, group = parse_reviewer(payload.reviewer)
        if user:
            reviews = reviews.filter(reviewer_user=user)
        elif group:
            reviews = reviews.filter(reviewer_group=group)

    details = [review_to_detail(r) for r in reviews]
    res = PRReviewShowResponse(pull_request_id=payload.pull_request_id, reviews=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr_review/approve")
async def approve_review_endpoint(payload: PRReviewApproveRequest, request):
    def do_approve():
        pr = get_pull_request(payload.pull_request_id)
        latest_revision = pr.revisions.order_by("-revision_number").first()

        review = get_review_for_request(latest_revision, payload.reviewer)
        review.state = PullRequestReview.State.ACCEPTED
        user = get_authenticated_user(request)
        review.actor = user
        review.justification = None
        review.save()

        res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
        return msgspec.structs.asdict(res)
    return await sync_to_async(do_approve)()


@api.post("/api/v1/pr_review/decline")
async def decline_review_endpoint(payload: PRReviewDeclineRequest, request):
    def do_decline():
        pr = get_pull_request(payload.pull_request_id)
        latest_revision = pr.revisions.order_by("-revision_number").first()

        review = get_review_for_request(latest_revision, payload.reviewer)
        review.state = PullRequestReview.State.REJECTED
        user = get_authenticated_user(request)
        review.actor = user
        review.justification = payload.message
        review.save()

        res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
        return msgspec.structs.asdict(res)
    return await sync_to_async(do_decline)()


@api.post("/api/v1/pr_review/needinfo")
async def needinfo_review_endpoint(payload: PRReviewNeedInfoRequest, request):
    def do_needinfo():
        pr = get_pull_request(payload.pull_request_id)
        latest_revision = pr.revisions.order_by("-revision_number").first()

        review = get_review_for_request(latest_revision, payload.reviewer)
        review.state = PullRequestReview.State.NEEDINFO
        user = get_authenticated_user(request)
        review.actor = user
        review.justification = payload.message
        review.save()

        res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
        return msgspec.structs.asdict(res)
    return await sync_to_async(do_needinfo)()


@api.post("/api/v1/pr_review/clear_needinfo")
async def clear_needinfo_review_endpoint(payload: PRReviewClearNeedInfoRequest, request):
    def do_clear_needinfo():
        pr = get_pull_request(payload.pull_request_id)
        latest_revision = pr.revisions.order_by("-revision_number").first()

        # Clear needinfo on all reviews for this revision that are in NEEDINFO state
        reviews = latest_revision.reviews.filter(state=PullRequestReview.State.NEEDINFO)
        user = get_authenticated_user(request)

        last_review = None
        for review in reviews:
            review.state = PullRequestReview.State.PENDING
            review.actor = user
            review.justification = payload.message
            review.save()
            last_review = review

        if not last_review:
            # If no reviews were in NEEDINFO, just get/create a default one to return
            last_review = get_review_for_request(latest_revision, None)

        res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(last_review))
        return msgspec.structs.asdict(res)
    return await sync_to_async(do_clear_needinfo)()


@api.post("/api/v1/pr_review/reopen")
async def reopen_review_endpoint(payload: PRReviewReopenRequest, request):
    def do_reopen():
        pr = get_pull_request(payload.pull_request_id)
        latest_revision = pr.revisions.order_by("-revision_number").first()

        review = get_review_for_request(latest_revision, payload.reviewer)
        review.state = PullRequestReview.State.PENDING
        user = get_authenticated_user(request)
        review.actor = user
        review.justification = payload.message
        review.save()

        res = PRReviewActionResponse(pull_request_id=payload.pull_request_id, review=review_to_detail(review))
        return msgspec.structs.asdict(res)
    return await sync_to_async(do_reopen)()


import urllib.request
import urllib.error
import json
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseServerError


@transaction.atomic
def provision_reviews_for_revision(revision: PullRequestRevision) -> list[PullRequestReview]:
    """
    Provisions reviews for a PullRequestRevision based on ReviewConfig if no reviews exist.
    While a revision is in draft mode, no review records are created.
    Existing reviews are never re-provisioned.
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
        configs = ReviewConfig.objects.filter(project=project, type=config_type)
        config_to_review = {}
        for config in configs:
            review = PullRequestReview.objects.create(
                revision=rev,
                reviewer_user=config.reviewer_user,
                reviewer_group=config.reviewer_group,
                dynamic_role=config.dynamic_role,
                state=PullRequestReview.State.WAITING,
            )
            config_to_review[config] = review
            created_reviews.append(review)

        # Set up dependencies between the created reviews
        for config, review in config_to_review.items():
            for dep_config in config.depends_on.all():
                if dep_config in config_to_review:
                    review.depends_on.add(config_to_review[dep_config])

        # Reviews with no dependencies start as PENDING, others remain WAITING
        for review in created_reviews:
            if not review.depends_on.exists():
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
    latest_revision = pr.revisions.order_by("-revision_number").first()
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
        from staging.models import StagingBatch
        from staging.api import create_staging_revision

        affected_batches = StagingBatch.objects.filter(
            revisions__revision_pull_requests__pull_request_revision__pull_request=pr
        ).distinct()

        for batch in affected_batches:
            latest_rev = batch.revisions.order_by("-revision_number").first()
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
                            updated_pr_revs.append(latest_revision)
                        else:
                            updated_pr_revs.append(r)
                    create_staging_revision(batch, updated_pr_revs)
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
        pull_request=PRDetail(
            id=f"{req.owner}/{req.repo}#{req.number}",
            title=pr.title,
            state=pr.state,
            is_draft=pr.is_draft,
            is_mergeable=pr.is_mergeable,
            author=build_user_dto(pr.author),
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


@api.post("/api/v1/pr/ready-for-review")
@sync_to_async
def pr_ready_for_review_endpoint(payload: PRReadyForReviewRequest):
    updated_prs = []
    for pr_id in payload.pull_request_ids:
        try:
            pr = get_pull_request(pr_id)
        except (PullRequest.DoesNotExist, ValueError) as e:
            return HttpResponseBadRequest(str(e))

        latest_revision = pr.revisions.order_by("-revision_number").first()
        if not latest_revision:
            return HttpResponseBadRequest(f"Pull request {pr_id} has no revisions.")

        mark_ready_for_review(latest_revision)
        pr.refresh_from_db()
        latest_revision.refresh_from_db()
        updated_prs.append(
            PRDetail(
                id=pr_id,
                title=pr.title,
                state=pr.state,
                is_draft=pr.is_draft,
                is_mergeable=pr.is_mergeable,
                author=build_user_dto(pr.author),
                latest_revision=latest_revision.revision_number,
                head_sha=latest_revision.head_sha,
                base_sha=latest_revision.base_sha,
            )
        )

    res = PRReadyForReviewResponse(pull_requests=updated_prs)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/pr/convert-to-draft")
@sync_to_async
def pr_convert_to_draft_endpoint(payload: PRConvertToDraftRequest):
    updated_prs = []
    for pr_id in payload.pull_request_ids:
        try:
            pr = get_pull_request(pr_id)
        except (PullRequest.DoesNotExist, ValueError) as e:
            return HttpResponseBadRequest(str(e))

        latest_revision = pr.revisions.order_by("-revision_number").first()
        if not latest_revision:
            return HttpResponseBadRequest(f"Pull request {pr_id} has no revisions.")

        mark_draft(latest_revision)
        pr.refresh_from_db()
        latest_revision.refresh_from_db()
        updated_prs.append(
            PRDetail(
                id=pr_id,
                title=pr.title,
                state=pr.state,
                is_draft=pr.is_draft,
                is_mergeable=pr.is_mergeable,
                author=build_user_dto(pr.author),
                latest_revision=latest_revision.revision_number,
                head_sha=latest_revision.head_sha,
                base_sha=latest_revision.base_sha,
            )
        )

    res = PRConvertToDraftResponse(pull_requests=updated_prs)
    return msgspec.structs.asdict(res)
