import datetime
import urllib.parse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from core.htmx import close_modal_and_refresh
from core.models import Project
from pull_requests.models import PullRequest
from pull_requests.forms import PullRequestFilterForm
from pull_requests.workflows import execute_pr_merge, mark_draft, mark_ready_for_review, validate_pr_merge


def get_pr_list_context(request, qs):
    form = PullRequestFilterForm(request.GET)

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
                qs = qs.filter(project__org__name__iexact=target_owner)
            else:
                qs = qs.filter(project__org__name__icontains=target_owner)
        if target_repo:
            if target_repo_exact:
                if target_repo.lower() == "_project":
                    qs = qs.filter(package__isnull=True)
                else:
                    qs = qs.filter(package__name__iexact=target_repo)
            else:
                if "_project".startswith(target_repo.lower()):
                    qs = qs.filter(Q(package__name__icontains=target_repo) | Q(package__isnull=True))
                else:
                    qs = qs.filter(package__name__icontains=target_repo)
        if target_branch:
            if target_branch_exact:
                qs = qs.filter(project__branch_name__iexact=target_branch)
            else:
                qs = qs.filter(project__branch_name__icontains=target_branch)

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

    allowed_sorts = ['id', 'title', 'author__username', 'target__branch', 'project__branch_name', 'is_mergeable', 'state']
    sort_param = request.GET.get('sort', '-id')
    if sort_param.lstrip('-') not in allowed_sorts:
        sort_param = '-id'

    sort_field = sort_param.replace('target__branch', 'project__branch_name')
    qs = qs.order_by(sort_field)

    page_size = request.user.page_size if request.user.is_authenticated else 100
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    base_params = {k: v for k, v in request.GET.items() if k not in ['page', 'sort'] and v}
    base_query = "&" + urllib.parse.urlencode(base_params) if base_params else ""

    page_params = {k: v for k, v in request.GET.items() if k != 'page' and v}
    filter_query = "&" + urllib.parse.urlencode(page_params) if page_params else ""

    return {
        "form": form,
        "page_obj": page_obj,
        "filter_query": filter_query,
        "base_query": base_query,
        "current_sort": sort_param,
        "total_count": paginator.count,
    }


@ensure_csrf_cookie
def pr_list(request):
    qs = PullRequest.objects.select_related("project", "project__org", "package", "author").all()
    context = get_pr_list_context(request, qs)
    return render(request, "pull_requests/pr_list.html", context)


@ensure_csrf_cookie
def project_pr_list(request, project_name):
    project = get_object_or_404(Project.objects.select_related("org"), name=project_name)
    qs = PullRequest.objects.select_related("project", "project__org", "package", "author").filter(project=project)
    context = get_pr_list_context(request, qs)
    context["project"] = project
    context["active_tab"] = "pull_requests"
    return render(request, "core/project_pr_list.html", context)


@ensure_csrf_cookie
def package_pr_list(request, project_name, package_name):
    from core.models import Package
    package = get_object_or_404(Package.objects.select_related("project", "project__org"),
        project__name=project_name,
        name=package_name,
    )
    qs = PullRequest.objects.select_related("project", "project__org", "package", "author").filter(package=package)
    context = get_pr_list_context(request, qs)
    context["package"] = package
    context["active_tab"] = "pull_requests"
    return render(request, "core/package_pr_list.html", context)


def get_pr_or_404(project_name, number, package_name=None):
    qs = PullRequest.objects.select_related("project", "project__org", "package", "package__project", "author")
    if package_name is None:
        return get_object_or_404(qs, project__name=project_name, package__isnull=True, number=number)
    return get_object_or_404(qs, project__name=project_name, package__name=package_name, number=number)


def pr_detail(request, project_name, number, package_name=None):
    pr = get_pr_or_404(project_name, number, package_name)
    revisions = pr.revisions.all().order_by("-revision_number")
    latest_revision = revisions.first()
    reviews = latest_revision.reviews.all() if latest_revision else []
    return render(
        request,
        "pull_requests/pr_detail.html",
        {
            "pr": pr,
            "project": pr.project,
            "package": pr.package,
            "active_tab": "pull_requests",
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


def pr_draft_status(request, project_name, number, package_name=None):
    pr = get_pr_or_404(project_name, number, package_name)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision and latest_revision.is_draft and latest_revision.draft_expires_at and latest_revision.draft_expires_at <= timezone.now():
        mark_ready_for_review(latest_revision)
        pr.refresh_from_db()
        latest_revision.refresh_from_db()
    return _render_pr_draft_section(request, pr, latest_revision)


@require_POST
def pr_ready_for_review(request, project_name, number, package_name=None):
    pr = get_pr_or_404(project_name, number, package_name)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision:
        mark_ready_for_review(latest_revision)
        messages.success(request, f"Pull request #{pr.number} is now ready for review.")
        pr.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_pr_draft_section(request, pr, latest_revision)
    return redirect(pr)


@require_POST
def pr_cancel_timeout(request, project_name, number, package_name=None):
    pr = get_pr_or_404(project_name, number, package_name)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision:
        mark_draft(latest_revision)
        messages.success(request, f"Cancelled review debounce timeout for PR #{pr.number}.")
        pr.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_pr_draft_section(request, pr, latest_revision)
    return redirect(pr)


@require_POST
def pr_convert_to_draft(request, project_name, number, package_name=None):
    pr = get_pr_or_404(project_name, number, package_name)
    latest_revision = pr.revisions.order_by("-revision_number").first()
    if latest_revision:
        mark_draft(latest_revision)
        messages.success(request, f"Pull request #{pr.number} converted to draft.")
        pr.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_pr_draft_section(request, pr, latest_revision)
    return redirect(pr)


@require_POST
def pr_merge_action(request, project_name, number, package_name=None):
    pr = get_pr_or_404(project_name, number, package_name)
    reasons = validate_pr_merge(pr)
    if reasons:
        messages.error(request, "; ".join(reasons))
        return redirect(pr)

    try:
        execute_pr_merge(pr)
        messages.success(request, f"Pull request #{pr.number} merged successfully.")
    except Exception as e:
        messages.error(request, str(e))

    return redirect(pr)


@require_POST
def pr_bulk_merge(request):
    pr_ids = request.POST.getlist("selected_prs")
    if not pr_ids:
        messages.warning(request, "No pull requests selected for merge.")
        return redirect("pr_list")


    merged_count = 0
    errors = []
    for pr_id in pr_ids:
        try:
            pr = get_object_or_404(PullRequest, id=pr_id)
            reasons = validate_pr_merge(pr)
            if reasons:
                errors.append(f"PR #{pr.number}: {'; '.join(reasons)}")
                continue

            execute_pr_merge(pr)
            merged_count += 1
        except Exception as e:
            errors.append(str(e))

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} pull request(s).")
    for err in errors:
        messages.error(request, err)

    return redirect("pr_list")




@require_POST
def pr_ui_modal_check_merge(request):
    pr_ids = request.POST.getlist("selected_prs")
    items = []
    mergeable_prs = []

    for pr_id in pr_ids:
        try:
            pr = PullRequest.objects.get(id=pr_id)
            reasons = validate_pr_merge(pr)
            items.append({
                "pr": pr,
                "can_merge": not reasons,
                "error": "; ".join(reasons),
            })
            if not reasons:
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
        return close_modal_and_refresh()


    merged_count = 0
    errors = []
    for pr_id in pr_ids:
        try:
            pr = PullRequest.objects.get(id=pr_id)
            reasons = validate_pr_merge(pr)
            if reasons:
                errors.append(f"PR #{pr.number}: {'; '.join(reasons)}")
                continue

            execute_pr_merge(pr)
            merged_count += 1
        except Exception as e:
            errors.append(f"PR #{pr_id}: {e}")

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} pull request(s).")
    for err in errors:
        messages.error(request, err)

    return close_modal_and_refresh()


