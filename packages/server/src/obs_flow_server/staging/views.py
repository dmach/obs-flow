from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from accounts.models import User
from core.models import Project
from staging.models import StagingBatch


def update_staging_batch(batch_id: int, title=None, embargo_date=None, release_date=None) -> StagingBatch:
    batch = StagingBatch.objects.get(id=batch_id)

    if title is not None:
        batch.title = title
    if embargo_date is not None:
        if embargo_date == "":
            batch.embargo_date = None
        elif isinstance(embargo_date, str):
            batch.embargo_date = timezone.datetime.fromisoformat(embargo_date)
        else:
            batch.embargo_date = embargo_date

    if release_date is not None:
        if release_date == "":
            batch.release_date = None
        elif isinstance(release_date, str):
            batch.release_date = timezone.datetime.fromisoformat(release_date)
        else:
            batch.release_date = release_date

    batch.save()
    return batch


def staging_list(request):
    batches = StagingBatch.objects.all().order_by("-id")
    return render(request, "staging/staging_list.html", {"batches": batches})


def staging_detail(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)

    pull_requests_data = []
    for bpr in batch.batch_pull_requests.all():
        pr = bpr.pull_request
        latest_rev = pr.revisions.order_by("-revision_number").first()
        if latest_rev:
            total_reviews = latest_rev.reviews.count()
            accepted_reviews = latest_rev.reviews.filter(state="accepted").count()
        else:
            total_reviews = 0
            accepted_reviews = 0

        pull_requests_data.append(
            {
                "pr": pr,
                "accepted_reviews": accepted_reviews,
                "total_reviews": total_reviews,
            }
        )

    reviews = batch.reviews.all()
    return render(
        request,
        "staging/staging_detail.html",
        {
            "batch": batch,
            "pull_requests_data": pull_requests_data,
            "reviews": reviews,
        },
    )


def staging_edit_date_form(request, batch_id, date_type):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    current_val = getattr(batch, f"{date_type}_date")
    val_str = current_val.strftime("%Y-%m-%dT%H:%M") if current_val else ""
    return render(
        request, "staging/partials/date_form.html", {"batch": batch, "date_type": date_type, "current_val": val_str}
    )


def staging_edit_date(request, batch_id, date_type):
    if request.method == "POST":
        new_val = request.POST.get("date_value", "")
        kwargs = {f"{date_type}_date": new_val}
        batch = update_staging_batch(batch_id, **kwargs)
        return render(request, "staging/partials/date_display.html", {"batch": batch, "date_type": date_type})
    return HttpResponse(status=405)


def staging_date_display(request, batch_id, date_type):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    return render(request, "staging/partials/date_display.html", {"batch": batch, "date_type": date_type})
