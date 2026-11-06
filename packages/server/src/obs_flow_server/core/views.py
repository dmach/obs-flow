import urllib.parse
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie

from core.models import Project, Package
from core.forms import ProjectFilterForm, PackageFilterForm


def home(request):
    return render(
        request,
        "core/home.html",
    )


@ensure_csrf_cookie
def project_list(request):
    form = ProjectFilterForm(request.GET)
    qs = Project.objects.select_related("org").all()

    if form.is_valid():
        name = form.cleaned_data.get("name")
        name_exact = form.cleaned_data.get("name_exact")
        org = form.cleaned_data.get("org")
        org_exact = form.cleaned_data.get("org_exact")
        branch_name = form.cleaned_data.get("branch_name")
        branch_name_exact = form.cleaned_data.get("branch_name_exact")
        workflow_type = form.cleaned_data.get("workflow_type")

        if name:
            if name_exact:
                qs = qs.filter(name__iexact=name)
            else:
                qs = qs.filter(name__icontains=name)

        if org:
            if org_exact:
                qs = qs.filter(org__name__iexact=org)
            else:
                qs = qs.filter(org__name__icontains=org)

        if branch_name:
            if branch_name_exact:
                qs = qs.filter(branch_name__iexact=branch_name)
            else:
                qs = qs.filter(branch_name__icontains=branch_name)

        if workflow_type:
            qs = qs.filter(workflow_type=workflow_type)

    allowed_sorts = ["name", "org__name", "branch_name", "workflow_type"]
    sort_param = request.GET.get("sort", "name")
    if sort_param.lstrip("-") not in allowed_sorts:
        sort_param = "name"
    qs = qs.order_by(sort_param)

    page_size = request.user.page_size if request.user.is_authenticated else 50
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    base_params = {k: v for k, v in request.GET.items() if k not in ["page", "sort"] and v}
    base_query = "&" + urllib.parse.urlencode(base_params) if base_params else ""

    page_params = {k: v for k, v in request.GET.items() if k != "page" and v}
    filter_query = "&" + urllib.parse.urlencode(page_params) if page_params else ""

    return render(
        request,
        "core/project_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "filter_query": filter_query,
            "base_query": base_query,
            "current_sort": sort_param,
            "total_count": paginator.count,
        },
    )


def project_detail(request, project_name):
    project = get_object_or_404(Project.objects.select_related("org"), name=project_name)
    packages = project.packages.select_related("forked_from", "forked_from__project").all().order_by("name")

    return render(
        request,
        "core/project_detail.html",
        {
            "project": project,
            "packages": packages,
            "active_tab": "overview",
        },
    )


@ensure_csrf_cookie
def package_list(request):
    form = PackageFilterForm(request.GET)
    qs = Package.objects.select_related("project", "project__org", "forked_from", "forked_from__project").all()

    if form.is_valid():
        name = form.cleaned_data.get("name")
        name_exact = form.cleaned_data.get("name_exact")
        project = form.cleaned_data.get("project")
        project_exact = form.cleaned_data.get("project_exact")

        if name:
            if name_exact:
                qs = qs.filter(name__iexact=name)
            else:
                qs = qs.filter(name__icontains=name)

        if project:
            if project_exact:
                qs = qs.filter(project__name__iexact=project)
            else:
                qs = qs.filter(project__name__icontains=project)

    allowed_sorts = ["name", "project__name"]
    sort_param = request.GET.get("sort", "name")
    if sort_param.lstrip("-") not in allowed_sorts:
        sort_param = "name"
    qs = qs.order_by(sort_param)

    page_size = request.user.page_size if request.user.is_authenticated else 50
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    base_params = {k: v for k, v in request.GET.items() if k not in ["page", "sort"] and v}
    base_query = "&" + urllib.parse.urlencode(base_params) if base_params else ""

    page_params = {k: v for k, v in request.GET.items() if k != "page" and v}
    filter_query = "&" + urllib.parse.urlencode(page_params) if page_params else ""

    return render(
        request,
        "core/package_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "filter_query": filter_query,
            "base_query": base_query,
            "current_sort": sort_param,
            "total_count": paginator.count,
        },
    )


def package_detail(request, project_name, package_name):
    package = get_object_or_404(
        Package.objects.select_related("project", "project__org", "forked_from", "forked_from__project"),
        project__name=project_name,
        name=package_name,
    )
    forks = package.forks.select_related("project").all().order_by("project__name")

    return render(
        request,
        "core/package_detail.html",
        {
            "package": package,
            "forks": forks,
            "active_tab": "overview",
        },
    )
