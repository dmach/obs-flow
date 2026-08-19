from django.shortcuts import render

from core.models import Project, GitMapping
from pull_requests.models import PullRequest
from staging.models import StagingBatch


def home(request):
    return render(
        request,
        "core/home.html",
    )


def git_mapping_list(request):
    mappings = GitMapping.objects.select_related("project", "package", "package__project").all()
    return render(
        request,
        "core/git_mapping_list.html",
        {"mappings": mappings},
    )
