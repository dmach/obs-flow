import urllib.parse
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from core.models import Project
from pull_requests.models import PullRequest
from staging.models import StagingBatch, StagingReview
from staging.forms import StagingBatchFilterForm


def _close_modal_and_refresh() -> HttpResponse:
    """
    Close the htmx modal and reload the page.

    The reload re-renders the list with fresh data and unchecked checkboxes, and
    displays the queued django.contrib.messages as toasts - no JavaScript needed.
    """
    response = HttpResponse("")
    response["HX-Refresh"] = "true"
    return response


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
    can_merge = False
    if latest_revision and not latest_revision.is_draft and batch.state != StagingBatch.State.MERGED:
        if reviews.exists() and not reviews.exclude(state__in=[StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN]).exists():
            can_merge = True

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
        batch = update_staging_batch(batch_id, **kwargs)
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

    # If no resolution is specified, check for conflicts
    if not resolution:
        conflicts = []
        for pr_id in pr_ids:
            pr = get_object_or_404(PullRequest, id=pr_id)
            # Find other open staging batches containing this PR
            other_open_batches = StagingBatch.objects.filter(
                state__in=[StagingBatch.State.COLLECTING, StagingBatch.State.IN_PROGRESS],
                revisions__revision_pull_requests__pull_request_revision__pull_request=pr
            ).exclude(id=batch.id).distinct()

            if other_open_batches.exists():
                conflicts.append({
                    "pr": pr,
                    "other_batches": other_open_batches,
                })

        if conflicts:
            return render(request, "staging/partials/modal_conflicts.html", {
                "conflicts": conflicts,
                "selected_prs": pr_ids,
                "batch_id": batch_id,
            })

    # Perform the addition based on resolution
    prs_to_add = []
    for pr_id in pr_ids:
        pr = get_object_or_404(PullRequest, id=pr_id)
        if resolution == "safe":
            # Skip if in any other open batch
            other_open_batches = StagingBatch.objects.filter(
                state__in=[StagingBatch.State.COLLECTING, StagingBatch.State.IN_PROGRESS],
                revisions__revision_pull_requests__pull_request_revision__pull_request=pr
            ).exclude(id=batch.id).distinct()
            if other_open_batches.exists():
                continue
        prs_to_add.append(pr)

    if not prs_to_add:
        messages.error(request, "No pull requests were added (all were conflicting).")
        return _close_modal_and_refresh()

    # Get current PRs in the batch
    latest_rev = batch.revisions.order_by("-revision_number").first()
    current_prs = []
    if latest_rev:
        current_prs = [
            bpr.pull_request_revision.pull_request
            for bpr in latest_rev.revision_pull_requests.all()
        ]

    # Add new PRs
    for pr in prs_to_add:
        if pr not in current_prs:
            current_prs.append(pr)

    # Get latest revision for each PR
    pr_revisions = []
    for pr in current_prs:
        latest_pr_rev = pr.revisions.order_by("-revision_number").first()
        if latest_pr_rev:
            pr_revisions.append(latest_pr_rev)

    # imported here: staging.api imports staging.views, so a module level import would be circular
    from staging.api import create_staging_revision

    create_staging_revision(batch, pr_revisions)

    messages.success(request, f"Successfully added {len(prs_to_add)} PRs to Staging Batch #{batch.id}.")
    return _close_modal_and_refresh()


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
    latest_revision = batch.revisions.order_by("-revision_number").first()
    if latest_revision and latest_revision.is_draft and latest_revision.draft_expires_at and latest_revision.draft_expires_at <= timezone.now():
        from staging.api import mark_staging_ready_for_review
        mark_staging_ready_for_review(latest_revision)
        batch.refresh_from_db()
        latest_revision.refresh_from_db()
    return _render_staging_draft_section(request, batch, latest_revision)


@require_POST
def staging_ready_for_review(request, batch_id):
    batch = get_object_or_404(StagingBatch, id=batch_id)
    latest_revision = batch.revisions.order_by("-revision_number").first()
    if latest_revision:
        from staging.api import mark_staging_ready_for_review
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
    latest_revision = batch.revisions.order_by("-revision_number").first()
    if latest_revision:
        from staging.api import mark_staging_draft
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
    latest_revision = batch.revisions.order_by("-revision_number").first()
    if latest_revision:
        from staging.api import mark_staging_draft
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
    if batch.state == StagingBatch.State.MERGED:
        messages.error(request, f"Staging batch #{batch.id} is already merged.")
        return redirect("staging_detail", batch_id=batch.id)

    latest_rev = batch.revisions.order_by("-revision_number").first()
    if not latest_rev:
        messages.error(request, f"Staging batch #{batch.id} has no revisions.")
        return redirect("staging_detail", batch_id=batch.id)

    if latest_rev.is_draft:
        messages.error(request, f"Staging batch #{batch.id} is currently in draft mode and cannot be merged.")
        return redirect("staging_detail", batch_id=batch.id)

    unapproved = latest_rev.reviews.exclude(state__in=[StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN])
    if unapproved.exists():
        names = [str(r.reviewer_user or r.reviewer_group or r.dynamic_role) for r in unapproved]
        messages.error(request, f"Cannot merge staging batch #{batch.id}: unapproved reviews: {', '.join(names)}.")
        return redirect("staging_detail", batch_id=batch.id)

    from pull_requests.api import _do_gitea_merge
    prs = [bpr.pull_request_revision.pull_request for bpr in latest_rev.revision_pull_requests.all()]
    for pr in prs:
        if pr.state != PullRequest.State.MERGED:
            try:
                _do_gitea_merge(pr.target.owner, pr.target.repo, pr.number)
                pr.state = PullRequest.State.MERGED
                pr.save(update_fields=["state"])
            except Exception as e:
                messages.error(request, f"Failed to merge PR #{pr.number}: {e}")
                return redirect("staging_detail", batch_id=batch.id)

    batch.state = StagingBatch.State.MERGED
    batch.closed_at = timezone.now()
    batch.save(update_fields=["state", "closed_at"])
    messages.success(request, f"Staging batch #{batch.id} merged successfully.")
    return redirect("staging_detail", batch_id=batch.id)


@require_POST
def staging_bulk_merge(request):
    batch_ids = request.POST.getlist("selected_batches")
    if not batch_ids:
        messages.warning(request, "No staging batches selected for merge.")
        return redirect("staging_list")

    from pull_requests.api import _do_gitea_merge

    merged_count = 0
    errors = []
    for b_id in batch_ids:
        try:
            batch = get_object_or_404(StagingBatch, id=b_id)
            if batch.state == StagingBatch.State.MERGED:
                errors.append(f"Batch #{batch.id}: Already merged.")
                continue

            latest_rev = batch.revisions.order_by("-revision_number").first()
            if not latest_rev or latest_rev.is_draft:
                errors.append(f"Batch #{batch.id}: In draft or no revisions.")
                continue

            unapproved = latest_rev.reviews.exclude(state__in=[StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN])
            if unapproved.exists():
                names = [str(r.reviewer_user or r.reviewer_group or r.dynamic_role) for r in unapproved]
                errors.append(f"Batch #{batch.id}: Unapproved reviews: {', '.join(names)}.")
                continue

            prs = [bpr.pull_request_revision.pull_request for bpr in latest_rev.revision_pull_requests.all()]
            for pr in prs:
                if pr.state != PullRequest.State.MERGED:
                    _do_gitea_merge(pr.target.owner, pr.target.repo, pr.number)
                    pr.state = PullRequest.State.MERGED
                    pr.save(update_fields=["state"])

            batch.state = StagingBatch.State.MERGED
            batch.closed_at = timezone.now()
            batch.save(update_fields=["state", "closed_at"])
            merged_count += 1
        except Exception as e:
            errors.append(str(e))

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} staging batch(es).")
    for err in errors:
        messages.error(request, err)

    return redirect("staging_list")


def _check_staging_for_merge(batch: StagingBatch) -> tuple[bool, str | None, list, list]:
    if batch.state == StagingBatch.State.MERGED:
        return False, "Staging batch is already merged.", [], []

    latest_rev = batch.revisions.order_by("-revision_number").first()
    if not latest_rev:
        return False, "Staging batch has no revisions.", [], []

    if latest_rev.is_draft:
        return False, "Staging batch is currently in draft mode and cannot be merged.", [], []

    reviews = list(latest_rev.reviews.all())
    unapproved = latest_rev.reviews.exclude(state__in=[StagingReview.State.ACCEPTED, StagingReview.State.OVERRIDDEN])
    if unapproved.exists():
        names = [r.reviewer_name for r in unapproved]
        return False, f"Unapproved reviews: {', '.join(names)}.", reviews, []

    prs = [bpr.pull_request_revision.pull_request for bpr in latest_rev.revision_pull_requests.all()]
    for pr in prs:
        if pr.is_draft:
            return False, f"Pull request #{pr.number} in batch is in draft mode.", reviews, prs
        if pr.is_mergeable is False:
            return False, f"Pull request #{pr.number} in batch has merge conflicts.", reviews, prs

    return True, None, reviews, prs


@require_POST
def staging_ui_modal_check_merge(request):
    batch_ids = request.POST.getlist("selected_batches")
    items = []
    mergeable_batches = []

    for b_id in batch_ids:
        try:
            batch = StagingBatch.objects.get(id=b_id)
            can_merge, error, reviews, prs = _check_staging_for_merge(batch)
            items.append({
                "batch": batch,
                "can_merge": can_merge,
                "error": error,
                "reviews": reviews,
                "prs": prs,
            })
            if can_merge:
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
        return _close_modal_and_refresh()

    from pull_requests.api import _do_gitea_merge

    merged_count = 0
    errors = []
    for b_id in batch_ids:
        try:
            batch = StagingBatch.objects.get(id=b_id)
            can_merge, error, _, prs = _check_staging_for_merge(batch)
            if not can_merge:
                errors.append(f"Batch #{batch.id}: {error}")
                continue

            for pr in prs:
                if pr.state != PullRequest.State.MERGED:
                    _do_gitea_merge(pr.target.owner, pr.target.repo, pr.number)
                    pr.state = PullRequest.State.MERGED
                    pr.save(update_fields=["state"])

            batch.state = StagingBatch.State.MERGED
            batch.closed_at = timezone.now()
            batch.save(update_fields=["state", "closed_at"])
            merged_count += 1
        except Exception as e:
            errors.append(f"Batch #{b_id}: {e}")

    if merged_count > 0:
        messages.success(request, f"Successfully merged {merged_count} staging batch(es).")
    for err in errors:
        messages.error(request, err)

    return _close_modal_and_refresh()


