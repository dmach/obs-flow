from django.shortcuts import render

from core.models import Project
from pull_requests.models import PullRequest
from staging.models import StagingBatch


def home(request):
    return render(
        request,
        "core/home.html",
    )
