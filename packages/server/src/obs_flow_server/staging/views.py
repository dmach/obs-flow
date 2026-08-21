import urllib.parse
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from accounts.models import User
from core.models import Project
from staging.models import StagingBatch
from staging.forms import StagingBatchFilterForm


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
    form = StagingBatchFilterForm(request.GET)
    qs = StagingBatch.objects.select_related("project", "author").all().order_by("-id")

    if form.is_valid():
        target_owner = form.cleaned_data.get("target_owner")
        target_owner_exact = form.cleaned_data.get("target_owner_exact")
        target_branch = form.cleaned_data.get("target_branch")
        target_branch_exact = form.cleaned_data.get("target_branch_exact")
        pr_title = form.cleaned_data.get("pr_title")
        pr_title_exact = form.cleaned_data.get("pr_title_exact")
        pr_author = form.cleaned_data.get("pr_author")
        pr_author_exact = form.cleaned_data.get("pr_author_exact")
        pr_source_owner = form.cleaned_data.get("pr_source_owner")
        pr_source_owner_exact = form.cleaned_data.get("pr_source_owner_exact")
        pr_source_repo = form.cleaned_data.get("pr_source_repo")
        pr_source_repo_exact = form.cleaned_data.get("pr_source_repo_exact")
        pr_source_branch = form.cleaned_data.get("pr_source_branch")
        pr_source_branch_exact = form.cleaned_data.get("pr_source_branch_exact")
        pr_target_owner = form.cleaned_data.get("pr_target_owner")
        pr_target_owner_exact = form.cleaned_data.get("pr_target_owner_exact")
        pr_target_repo = form.cleaned_data.get("pr_target_repo")
        pr_target_repo_exact = form.cleaned_data.get("pr_target_repo_exact")
        pr_target_branch = form.cleaned_data.get("pr_target_branch")
        pr_target_branch_exact = form.cleaned_data.get("pr_target_branch_exact")

        if target_owner:
            if target_owner_exact:
                qs = qs.filter(project__name__iexact=target_owner)
            else:
                qs = qs.filter(project__name__icontains=target_owner)
        if target_branch:
            if target_branch_exact:
                qs = qs.filter(batch_pull_requests__pull_request__target__branch__iexact=target_branch)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__target__branch__icontains=target_branch)

        if pr_title:
            if pr_title_exact:
                qs = qs.filter(batch_pull_requests__pull_request__title__iexact=pr_title)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__title__icontains=pr_title)
        if pr_author:
            if pr_author_exact:
                qs = qs.filter(batch_pull_requests__pull_request__author__username__iexact=pr_author)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__author__username__icontains=pr_author)
        if pr_source_owner:
            if pr_source_owner_exact:
                qs = qs.filter(batch_pull_requests__pull_request__source_owner__iexact=pr_source_owner)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__source_owner__icontains=pr_source_owner)
        if pr_source_repo:
            if pr_source_repo_exact:
                qs = qs.filter(batch_pull_requests__pull_request__source_repo__iexact=pr_source_repo)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__source_repo__icontains=pr_source_repo)
        if pr_source_branch:
            if pr_source_branch_exact:
                qs = qs.filter(batch_pull_requests__pull_request__source_branch__iexact=pr_source_branch)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__source_branch__icontains=pr_source_branch)
        if pr_target_owner:
            if pr_target_owner_exact:
                qs = qs.filter(batch_pull_requests__pull_request__target__owner__iexact=pr_target_owner)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__target__owner__icontains=pr_target_owner)
        if pr_target_repo:
            if pr_target_repo_exact:
                qs = qs.filter(batch_pull_requests__pull_request__target__repo__iexact=pr_target_repo)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__target__repo__icontains=pr_target_repo)
        if pr_target_branch:
            if pr_target_branch_exact:
                qs = qs.filter(batch_pull_requests__pull_request__target__branch__iexact=pr_target_branch)
            else:
                qs = qs.filter(batch_pull_requests__pull_request__target__branch__icontains=pr_target_branch)

        qs = qs.distinct()

    paginator = Paginator(qs, 200)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    filter_params = {k: v for k, v in request.GET.items() if k != 'page' and v}
    filter_query = "&" + urllib.parse.urlencode(filter_params) if filter_params else ""

    return render(
        request,
        "staging/staging_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "filter_query": filter_query,
            "total_count": paginator.count,
        }
    )


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
