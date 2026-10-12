import datetime
import urllib.parse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from core.models import Project
from pull_requests.models import PullRequest, PullRequestReview
from pull_requests.forms import PullRequestFilterForm


@ensure_csrf_cookie
def pr_list(request):
    form = PullRequestFilterForm(request.GET)
    qs = PullRequest.objects.select_related("target", "author").all().order_by("-id")

    if form.is_valid():
        title = form.cleaned_data.get("title")
        title_exact = form.cleaned_data.get("title_exact")
        author = form.cleaned_data.get("author")
        author_exact = form.cleaned_data.get("author_exact")
        in_progress_days = form.cleaned_data.get("in_progress_days")
        source_owner = form.cleaned_data.get("source_owner")
        source_owner_exact = form.cleaned_data.get("source_owner_exact")
        source_repo = form.cleaned_data.get("source_repo")
        source_repo_exact = form.cleaned_data.get("source_repo_exact")
        source_branch = form.cleaned_data.get("source_branch")
        source_branch_exact = form.cleaned_data.get("source_branch_exact")
        target_owner = form.cleaned_data.get("target_owner")
        target_owner_exact = form.cleaned_data.get("target_owner_exact")
        target_repo = form.cleaned_data.get("target_repo")
        target_repo_exact = form.cleaned_data.get("target_repo_exact")
        target_branch = form.cleaned_data.get("target_branch")
        target_branch_exact = form.cleaned_data.get("target_branch_exact")
        reviewer_person = form.cleaned_data.get("reviewer_person")
        reviewer_person_include_groups = form.cleaned_data.get("reviewer_person_include_groups")
        reviewer_group = form.cleaned_data.get("reviewer_group")

        if title:
            if title_exact:
                qs = qs.filter(title__iexact=title)
            else:
                qs = qs.filter(title__icontains=title)
        if author:
            if author_exact:
                qs = qs.filter(author__username__iexact=author)
            else:
                qs = qs.filter(author__username__icontains=author)
        if in_progress_days:
            now = timezone.now()
            qs = qs.filter(revisions__revision_number=1, revisions__created_at__lte=now - datetime.timedelta(days=in_progress_days))
        if source_owner:
            if source_owner_exact:
                qs = qs.filter(source_owner__iexact=source_owner)
            else:
                qs = qs.filter(source_owner__icontains=source_owner)
        if source_repo:
            if source_repo_exact:
                qs = qs.filter(source_repo__iexact=source_repo)
            else:
                qs = qs.filter(source_repo__icontains=source_repo)
        if source_branch:
            if source_branch_exact:
                qs = qs.filter(source_branch__iexact=source_branch)
            else:
                qs = qs.filter(source_branch__icontains=source_branch)
        if target_owner:
            if target_owner_exact:
                qs = qs.filter(target__owner__iexact=target_owner)
            else:
                qs = qs.filter(target__owner__icontains=target_owner)
        if target_repo:
            if target_repo_exact:
                qs = qs.filter(target__repo__iexact=target_repo)
            else:
                qs = qs.filter(target__repo__icontains=target_repo)
        if target_branch:
            if target_branch_exact:
                qs = qs.filter(target__branch__iexact=target_branch)
            else:
                qs = qs.filter(target__branch__icontains=target_branch)

        if reviewer_person:
            if reviewer_person_include_groups:
                qs = qs.filter(
                    Q(revisions__reviews__reviewer_user__username__iexact=reviewer_person) |
                    Q(revisions__reviews__reviewer_group__group_users__user__username__iexact=reviewer_person)
                ).distinct()
            else:
                qs = qs.filter(revisions__reviews__reviewer_user__username__iexact=reviewer_person).distinct()

        if reviewer_group:
            qs = qs.filter(revisions__reviews__reviewer_group__name__iexact=reviewer_group).distinct()

    allowed_sorts = ['id', 'title', 'author__username', 'target__branch', 'is_mergeable', 'state']
    sort_param = request.GET.get('sort', '-id')
    if sort_param.lstrip('-') not in allowed_sorts:
        sort_param = '-id'

    qs = qs.order_by(sort_param)

    page_size = request.user.page_size if request.user.is_authenticated else 100
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    base_params = {k: v for k, v in request.GET.items() if k not in ['page', 'sort'] and v}
    base_query = "&" + urllib.parse.urlencode(base_params) if base_params else ""

    page_params = {k: v for k, v in request.GET.items() if k != 'page' and v}
    filter_query = "&" + urllib.parse.urlencode(page_params) if page_params else ""

    return render(
        request,
        "pull_requests/pr_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "filter_query": filter_query,
            "base_query": base_query,
            "current_sort": sort_param,
            "total_count": paginator.count,
        }
    )


def pr_detail(request, pr_id):
    pr = get_object_or_404(PullRequest, id=pr_id)
    revisions = pr.revisions.all().order_by("-revision_number")
    latest_revision = revisions.first()
    reviews = latest_revision.reviews.all() if latest_revision else []
    return render(
        request,
        "pull_requests/pr_detail.html",
        {
            "pr": pr,
            "revisions": revisions,
            "latest_revision": latest_revision,
            "reviews": reviews,
        },
    )


def _render_pr_draft_section(request, pr, latest_revision):
    reviews = latest_revision.reviews.all() if latest_revision else []
    return render(
        request,
        "pull_requests/partials/draft_section.html",
        {
            "pr": pr,
            "latest_revision": latest_revision,
            "reviews": reviews,
        },
    )


def pr_draft_status(request, pr_id):
    pr = get_object_or_404(PullRequest, id=pr_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision and latest_revision.is_draft and latest_revision.draft_expires_at and latest_revision.draft_expires_at <= timezone.now():
        from pull_requests.api import mark_ready_for_review
        mark_ready_for_review(latest_revision)
        pr.refresh_from_db()
        latest_revision.refresh_from_db()
    return _render_pr_draft_section(request, pr, latest_revision)


@require_POST
def pr_ready_for_review(request, pr_id):
    pr = get_object_or_404(PullRequest, id=pr_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision:
        from pull_requests.api import mark_ready_for_review
        mark_ready_for_review(latest_revision)
        messages.success(request, f"Pull request #{pr.number} is now ready for review.")
        pr.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_pr_draft_section(request, pr, latest_revision)
    return redirect("pr_detail", pr_id=pr.id)


@require_POST
def pr_cancel_timeout(request, pr_id):
    pr = get_object_or_404(PullRequest, id=pr_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision:
        from pull_requests.api import mark_draft
        mark_draft(latest_revision)
        messages.success(request, f"Cancelled review debounce timeout for PR #{pr.number}.")
        pr.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_pr_draft_section(request, pr, latest_revision)
    return redirect("pr_detail", pr_id=pr.id)


@require_POST
def pr_convert_to_draft(request, pr_id):
    pr = get_object_or_404(PullRequest, id=pr_id)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision:
        from pull_requests.api import mark_draft
        mark_draft(latest_revision)
        messages.success(request, f"Pull request #{pr.number} converted to draft.")
        pr.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_pr_draft_section(request, pr, latest_revision)
    return redirect("pr_detail", pr_id=pr.id)


@require_POST
def pr_merge_action(request, pr_id):
    pr = get_object_or_404(PullRequest, id=pr_id)
    if pr.target_project and pr.target_project.workflow_type == Project.WorkflowType.STAGING:
        messages.error(
            request,
            f"Direct merges are not allowed for project '{pr.target_project.name}'. This PR must be merged via a staging batch."
        )
        return redirect("pr_detail", pr_id=pr.id)

    if pr.state == PullRequest.State.MERGED:
        messages.error(request, f"Pull request #{pr.number} is already merged.")
        return redirect("pr_detail", pr_id=pr.id)

    from pull_requests.api import _do_gitea_merge
    try:
        _do_gitea_merge(pr.target.owner, pr.target.repo, pr.number)
        pr.state = PullRequest.State.MERGED
        pr.save(update_fields=["state"])
        messages.success(request, f"Pull request #{pr.number} merged successfully.")
    except Exception as e:
        messages.error(request, str(e))

    return redirect("pr_detail", pr_id=pr.id)


@require_POST
def pr_bulk_merge(request):
    pr_ids = request.POST.getlist("selected_prs")
    if not pr_ids:
        messages.warning(request, "No pull requests selected for merge.")
        return redirect("pr_list")

    from pull_requests.api import _do_gitea_merge

    merged_count = 0
    errors = []
    for pr_id in pr_ids:
        try:
            pr = get_object_or_404(PullRequest, id=pr_id)
            if pr.target_project and pr.target_project.workflow_type == Project.WorkflowType.STAGING:
                errors.append(f"PR #{pr.number}: Direct merges disabled for project '{pr.target_project.name}'.")
                continue
            if pr.state == PullRequest.State.MERGED:
                errors.append(f"PR #{pr.number}: Already merged.")
                continue

            _do_gitea_merge(pr.target.owner, pr.target.repo, pr.number)
            pr.state = PullRequest.State.MERGED
            pr.save(update_fields=["state"])
            merged_count += 1
        except Exception as e:
            errors.append(str(e))

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} pull request(s).")
    for err in errors:
        messages.error(request, err)

    return redirect("pr_list")


def _close_modal_and_refresh() -> HttpResponse:
    response = HttpResponse("")
    response["HX-Refresh"] = "true"
    return response


def _check_pr_for_merge(pr: PullRequest) -> tuple[bool, str | None, list[str]]:
    warnings = []
    target_project = pr.target_project
    if target_project and target_project.workflow_type == Project.WorkflowType.STAGING:
        return False, f"Project '{target_project.name}' uses the staging workflow. Direct merges are disabled.", []

    if pr.state == PullRequest.State.MERGED:
        return False, f"Pull request #{pr.number} is already merged.", []

    if pr.state == PullRequest.State.CLOSED:
        return False, f"Pull request #{pr.number} is closed.", []

    latest_rev = pr.revisions.order_by("-revision_number").first()
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


@require_POST
def pr_ui_modal_check_merge(request):
    pr_ids = request.POST.getlist("selected_prs")
    items = []
    mergeable_prs = []

    for pr_id in pr_ids:
        try:
            pr = PullRequest.objects.get(id=pr_id)
            can_merge, error, warnings = _check_pr_for_merge(pr)
            items.append({
                "pr": pr,
                "can_merge": can_merge,
                "error": error,
                "warnings": warnings,
            })
            if can_merge:
                mergeable_prs.append(pr)
        except PullRequest.DoesNotExist:
            continue

    return render(
        request,
        "pull_requests/partials/modal_merge_check.html",
        {
            "items": items,
            "mergeable_prs": mergeable_prs,
        },
    )


@require_POST
def pr_ui_modal_execute_merge(request):
    pr_ids = request.POST.getlist("selected_prs")
    if not pr_ids:
        messages.warning(request, "No pull requests selected for merge.")
        return _close_modal_and_refresh()

    from pull_requests.api import _do_gitea_merge

    merged_count = 0
    errors = []
    for pr_id in pr_ids:
        try:
            pr = PullRequest.objects.get(id=pr_id)
            can_merge, error, _ = _check_pr_for_merge(pr)
            if not can_merge:
                errors.append(f"PR #{pr.number}: {error}")
                continue

            _do_gitea_merge(pr.target.owner, pr.target.repo, pr.number)
            pr.state = PullRequest.State.MERGED
            pr.save(update_fields=["state"])
            merged_count += 1
        except Exception as e:
            errors.append(f"PR #{pr_id}: {e}")

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} pull request(s).")
    for err in errors:
        messages.error(request, err)

    return _close_modal_and_refresh()


