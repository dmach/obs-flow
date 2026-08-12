from django.shortcuts import render, get_object_or_404

from pull_requests.models import PullRequest


def pr_list(request):
    pull_requests = PullRequest.objects.all().order_by("-id")
    return render(request, "pull_requests/pr_list.html", {"pull_requests": pull_requests})


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
