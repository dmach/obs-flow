import datetime
import urllib.parse
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from pull_requests.models import PullRequest
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

    paginator = Paginator(qs, 200)
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
