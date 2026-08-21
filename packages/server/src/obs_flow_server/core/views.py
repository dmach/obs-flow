import urllib.parse
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from core.models import Project, GitMapping
from core.forms import GitMappingFilterForm
from pull_requests.models import PullRequest
from staging.models import StagingBatch


def home(request):
    return render(
        request,
        "core/home.html",
    )


def git_mapping_list(request):
    form = GitMappingFilterForm(request.GET)
    qs = GitMapping.objects.select_related("project", "package", "package__project").all()

    if form.is_valid():
        owner = form.cleaned_data.get("owner")
        owner_exact = form.cleaned_data.get("owner_exact")
        repo = form.cleaned_data.get("repo")
        repo_exact = form.cleaned_data.get("repo_exact")
        branch = form.cleaned_data.get("branch")
        branch_exact = form.cleaned_data.get("branch_exact")
        project = form.cleaned_data.get("project")
        project_exact = form.cleaned_data.get("project_exact")
        package = form.cleaned_data.get("package")
        package_exact = form.cleaned_data.get("package_exact")

        if owner:
            if owner_exact:
                qs = qs.filter(owner__iexact=owner)
            else:
                qs = qs.filter(owner__icontains=owner)
        if repo:
            if repo_exact:
                qs = qs.filter(repo__iexact=repo)
            else:
                qs = qs.filter(repo__icontains=repo)
        if branch:
            if branch_exact:
                qs = qs.filter(branch__iexact=branch)
            else:
                qs = qs.filter(branch__icontains=branch)
        if project:
            if project_exact:
                qs = qs.filter(
                    Q(project__name__iexact=project) |
                    Q(package__project__name__iexact=project)
                )
            else:
                qs = qs.filter(
                    Q(project__name__icontains=project) |
                    Q(package__project__name__icontains=project)
                )
        if package:
            if package_exact:
                qs = qs.filter(package__name__iexact=package)
            else:
                qs = qs.filter(package__name__icontains=package)

    allowed_sorts = ['id', 'owner', 'repo', 'branch', 'project__name', 'package__name']
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
        "core/git_mapping_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "filter_query": filter_query,
            "base_query": base_query,
            "current_sort": sort_param,
            "total_count": paginator.count,
        },
    )
