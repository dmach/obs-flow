import urllib.parse
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.htmx import close_modal_and_refresh
from pull_requests.models import PullRequest
from staging.models import StagingBatch
from staging.forms import StagingBatchFilterForm
from staging.workflows import (
    batch_member_prs,
    execute_staging_merge,
    find_conflicts,
    mark_staging_draft,
    mark_staging_ready_for_review,
    rebuild_batch_revision,
    update_batch,
    validate_staging_merge,
)


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
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__branch__iexact=target_branch)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__branch__icontains=target_branch)

        if pr_title:
            if pr_title_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__title__iexact=pr_title)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__title__icontains=pr_title)
        if pr_author:
            if pr_author_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__author__username__iexact=pr_author)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__author__username__icontains=pr_author)
        if pr_source_owner:
            if pr_source_owner_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__source_owner__iexact=pr_source_owner)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__source_owner__icontains=pr_source_owner)
        if pr_source_repo:
            if pr_source_repo_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__source_repo__iexact=pr_source_repo)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__source_repo__icontains=pr_source_repo)
        if pr_source_branch:
            if pr_source_branch_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__source_branch__iexact=pr_source_branch)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__source_branch__icontains=pr_source_branch)
        if pr_target_owner:
            if pr_target_owner_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__owner__iexact=pr_target_owner)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__owner__icontains=pr_target_owner)
        if pr_target_repo:
            if pr_target_repo_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__repo__iexact=pr_target_repo)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__repo__icontains=pr_target_repo)
        if pr_target_branch:
            if pr_target_branch_exact:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__branch__iexact=pr_target_branch)
            else:
                qs = qs.filter(revisions__revision_pull_requests__pull_request_revision__pull_request__target__branch__icontains=pr_target_branch)

        qs = qs.distinct()

    allowed_sorts = ['id', 'title', 'project__name', 'author__username', 'state']
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
        "staging/staging_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "filter_query": filter_query,
            "base_query": base_query,
            "current_sort": sort_param,
            "total_count": paginator.count,
        }
    )


def staging_detail(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    revisions = batch.revisions.all().order_by("-revision_number")
    latest_revision = revisions.first()

    pull_requests_data = []
    if latest_revision:
        for bpr in latest_revision.revision_pull_requests.all():
            pr_rev = bpr.pull_request_revision
            pr = pr_rev.pull_request
            total_reviews = pr_rev.reviews.count()
            accepted_reviews = pr_rev.reviews.filter(state="accepted").count()
            pull_requests_data.append(
                {
                    "pr": pr,
                    "accepted_reviews": accepted_reviews,
                    "total_reviews": total_reviews,
                }
            )

    reviews = latest_revision.reviews.all() if latest_revision else []
    can_merge = validate_staging_merge(batch) == []

    return render(
        request,
        "staging/staging_detail.html",
        {
            "batch": batch,
            "revisions": revisions,
            "latest_revision": latest_revision,
            "pull_requests_data": pull_requests_data,
            "reviews": reviews,
            "can_merge": can_merge,
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
        batch = update_batch(batch_id, **kwargs)
        return render(request, "staging/partials/date_display.html", {"batch": batch, "date_type": date_type})
    return HttpResponse(status=405)


def staging_date_display(request, batch_id, date_type):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    return render(request, "staging/partials/date_display.html", {"batch": batch, "date_type": date_type})


def staging_ui_modal_select_batch(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    pr_ids = request.POST.getlist("selected_prs")
    if not pr_ids:
        return render(request, "staging/partials/modal_error.html", {"message": "No pull requests selected."})

    # Validate that all selected PRs target the same project
    projects = set()
    prs = []
    for pr_id in pr_ids:
        pr = get_object_or_404(PullRequest, id=pr_id)
        prs.append(pr)
        projects.add(pr.target_project)

    if len(projects) > 1:
        return render(request, "staging/partials/modal_error.html", {
            "message": "Selected pull requests must target the same project. Mixed projects are not allowed."
        })
    elif len(projects) == 0:
        return render(request, "staging/partials/modal_error.html", {
            "message": "Could not determine target project for selected pull requests."
        })

    project = list(projects)[0]
    batches = StagingBatch.objects.filter(
        project=project,
        state__in=[StagingBatch.State.COLLECTING, StagingBatch.State.IN_PROGRESS]
    ).order_by("-id")

    return render(request, "staging/partials/modal_select_batch.html", {
        "batches": batches,
        "selected_prs": pr_ids,
        "project": project,
    })


def staging_ui_modal_confirm_add(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    pr_ids = request.POST.getlist("selected_prs")
    batch_id = request.POST.get("batch_id")
    resolution = request.POST.get("resolution")

    if not pr_ids or not batch_id:
        return render(request, "staging/partials/modal_error.html", {"message": "Invalid request parameters."})

    batch = get_object_or_404(StagingBatch, id=batch_id)

    prs = [get_object_or_404(PullRequest, id=pr_id) for pr_id in pr_ids]

    # If no resolution is specified, check for conflicts
    if not resolution:
        conflicts = find_conflicts(batch, prs)
        if conflicts:
            return render(request, "staging/partials/modal_conflicts.html", {
                "conflicts": conflicts,
                "selected_prs": pr_ids,
                "batch_id": batch_id,
            })

    # Perform the addition based on resolution
    if resolution == "safe":
        # Skip PRs that are in any other open batch
        conflict_ids = {c["pr"].id for c in find_conflicts(batch, prs)}
        prs_to_add = [pr for pr in prs if pr.id not in conflict_ids]
    else:
        prs_to_add = list(prs)

    if not prs_to_add:
        messages.error(request, "No pull requests were added (all were conflicting).")
        return close_modal_and_refresh()

    # Add new PRs and rebuild the batch revision
    current_prs = batch_member_prs(batch)
    for pr in prs_to_add:
        if pr not in current_prs:
            current_prs.append(pr)

    rebuild_batch_revision(batch, current_prs)

    messages.success(request, f"Successfully added {len(prs_to_add)} PRs to Staging Batch #{batch.id}.")
    return close_modal_and_refresh()


def _render_staging_draft_section(request, batch, latest_revision):
    reviews = latest_revision.reviews.all() if latest_revision else []
    return render(
        request,
        "staging/partials/draft_section.html",
        {
            "batch": batch,
            "latest_revision": latest_revision,
            "reviews": reviews,
        },
    )


def staging_draft_status(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    latest_revision = batch.latest_revision
    if latest_revision and latest_revision.is_draft and latest_revision.draft_expires_at and latest_revision.draft_expires_at <= timezone.now():
        mark_staging_ready_for_review(latest_revision)
        batch.refresh_from_db()
        latest_revision.refresh_from_db()
    return _render_staging_draft_section(request, batch, latest_revision)


@require_POST
def staging_ready_for_review(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    latest_revision = batch.latest_revision
    if latest_revision:
        mark_staging_ready_for_review(latest_revision)
        messages.success(request, f"Staging batch #{batch.id} is now ready for review.")
        batch.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_staging_draft_section(request, batch, latest_revision)
    return redirect("staging_detail", batch_id=batch.id)


@require_POST
def staging_cancel_timeout(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    latest_revision = batch.latest_revision
    if latest_revision:
        mark_staging_draft(latest_revision)
        messages.success(request, f"Cancelled review debounce timeout for Staging Batch #{batch.id}.")
        batch.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_staging_draft_section(request, batch, latest_revision)
    return redirect("staging_detail", batch_id=batch.id)


@require_POST
def staging_convert_to_draft(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    latest_revision = batch.latest_revision
    if latest_revision:
        mark_staging_draft(latest_revision)
        messages.success(request, f"Staging batch #{batch.id} converted to draft.")
        batch.refresh_from_db()
        latest_revision.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_staging_draft_section(request, batch, latest_revision)
    return redirect("staging_detail", batch_id=batch.id)


@require_POST
def staging_merge_action(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    reasons = validate_staging_merge(batch)
    if reasons:
        messages.error(request, "; ".join(reasons))
        return redirect("staging_detail", batch_id=batch.id)

    try:
        execute_staging_merge(batch)
        messages.success(request, f"Staging batch #{batch.id} merged successfully.")
    except Exception as e:
        messages.error(request, str(e))

    return redirect("staging_detail", batch_id=batch.id)


@require_POST
def staging_bulk_merge(request):
    batch_ids = request.POST.getlist("selected_batches")
    if not batch_ids:
        messages.warning(request, "No staging batches selected for merge.")
        return redirect("staging_list")


    merged_count = 0
    errors = []
    for b_id in sorted(set(batch_ids)):
        try:
            batch = get_object_or_404(StagingBatch, id=b_id)
            reasons = validate_staging_merge(batch)
            if reasons:
                errors.append(f"Batch #{batch.id}: {'; '.join(reasons)}")
                continue

            execute_staging_merge(batch)
            merged_count += 1
        except Exception as e:
            errors.append(str(e))

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} staging batch(es).")
    for err in errors:
        messages.error(request, err)

    return redirect("staging_list")


@require_POST
def staging_ui_modal_check_merge(request):
    batch_ids = request.POST.getlist("selected_batches")
    items = []
    mergeable_batches = []

    for b_id in batch_ids:
        try:
            batch = StagingBatch.objects.get(id=b_id)
            reasons = validate_staging_merge(batch)
            latest_rev = batch.latest_revision
            items.append({
                "batch": batch,
                "can_merge": not reasons,
                "error": "; ".join(reasons),
                "reviews": list(latest_rev.reviews.all()) if latest_rev else [],
                "prs": batch_member_prs(batch),
            })
            if not reasons:
                mergeable_batches.append(batch)
        except StagingBatch.DoesNotExist:
            continue

    return render(
        request,
        "staging/partials/modal_merge_check.html",
        {
            "items": items,
            "mergeable_batches": mergeable_batches,
        },
    )


@require_POST
def staging_ui_modal_execute_merge(request):
    batch_ids = request.POST.getlist("selected_batches")
    if not batch_ids:
        messages.warning(request, "No staging batches selected for merge.")
        return close_modal_and_refresh()


    merged_count = 0
    errors = []
    for b_id in batch_ids:
        try:
            batch = StagingBatch.objects.get(id=b_id)
            reasons = validate_staging_merge(batch)
            if reasons:
                errors.append(f"Batch #{batch.id}: {'; '.join(reasons)}")
                continue

            execute_staging_merge(batch)
            merged_count += 1
        except Exception as e:
            errors.append(f"Batch #{b_id}: {e}")

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} staging batch(es).")
    for err in errors:
        messages.error(request, err)

    return close_modal_and_refresh()


