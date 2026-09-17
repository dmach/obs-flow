from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from bookmarks.models import Bookmark
from bookmarks.helpers import is_safe_url

def _close_modal_and_refresh() -> HttpResponse:
    response = HttpResponse("")
    response["HX-Refresh"] = "true"
    return response


@login_required
def bookmark_list(request):
    bookmarks = Bookmark.objects.filter(user=request.user)
    return render(request, "bookmarks/list.html", {"bookmarks": bookmarks})


@login_required
def bookmark_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        url = request.POST.get("url", "").strip()

        errors = {}
        if not name:
            errors["name"] = "Name cannot be empty."
        if not url:
            errors["url"] = "URL cannot be empty."
        elif not is_safe_url(url):
            errors["url"] = "Invalid URL: must be a relative path starting with '/'."

        if not errors:
            if Bookmark.objects.filter(user=request.user, name=name).exists():
                errors["name"] = "A bookmark with this name already exists."

        if errors:
            return render(
                request,
                "bookmarks/partials/create_modal.html",
                {"errors": errors, "name": name, "url": url},
            )

        Bookmark.objects.create(user=request.user, name=name, url=url)
        messages.success(request, f"Bookmark '{name}' saved successfully.")
        return _close_modal_and_refresh()

    # GET request
    url = request.GET.get("url", "").strip()
    # Try to suggest a default name based on the URL path
    name = ""
    if url:
        path_parts = [p for p in url.split("?")[0].split("/") if p]
        if path_parts:
            name = path_parts[-1].replace("-", " ").replace("_", " ").title()

    return render(
        request,
        "bookmarks/partials/create_modal.html",
        {"name": name, "url": url},
    )


@login_required
def bookmark_edit_inline(request, pk):
    bookmark = get_object_or_404(Bookmark, pk=pk, user=request.user)

    if request.method in ("POST", "PUT"):
        name = request.POST.get("name", "").strip()
        url = request.POST.get("url", "").strip()

        errors = {}
        if not name:
            errors["name"] = "Name cannot be empty."
        if not url:
            errors["url"] = "URL cannot be empty."
        elif not is_safe_url(url):
            errors["url"] = "Invalid URL: must be a relative path starting with '/'."

        if not errors:
            if Bookmark.objects.filter(user=request.user, name=name).exclude(pk=pk).exists():
                errors["name"] = "A bookmark with this name already exists."

        if errors:
            return render(
                request,
                "bookmarks/partials/inline_edit_row.html",
                {"bookmark": bookmark, "errors": errors, "name": name, "url": url},
            )

        bookmark.name = name
        bookmark.url = url
        bookmark.save()
        messages.success(request, f"Bookmark '{name}' updated successfully.")
        # Since we updated the bookmark, we can either return the read-only row or refresh the page
        # Refreshing is safer because the footer also needs to be updated!
        return _close_modal_and_refresh()

    # GET request
    return render(
        request,
        "bookmarks/partials/inline_edit_row.html",
        {"bookmark": bookmark, "name": bookmark.name, "url": bookmark.url},
    )


@login_required
def bookmark_cancel_edit(request, pk):
    bookmark = get_object_or_404(Bookmark, pk=pk, user=request.user)
    return render(
        request,
        "bookmarks/partials/inline_row.html",
        {"bookmark": bookmark},
    )


@login_required
def bookmark_delete_confirm(request):
    selected_ids = request.POST.getlist("selected_bookmarks")
    if not selected_ids:
        return render(
            request,
            "bookmarks/partials/modal_error.html",
            {"message": "No bookmarks selected."},
        )

    bookmarks_to_delete = Bookmark.objects.filter(user=request.user, id__in=selected_ids)
    count = bookmarks_to_delete.count()

    return render(
        request,
        "bookmarks/partials/delete_modal.html",
        {"count": count, "selected_ids": selected_ids},
    )


@login_required
def bookmark_delete_bulk(request):
    selected_ids = request.POST.getlist("selected_bookmarks")
    if selected_ids:
        bookmarks_to_delete = Bookmark.objects.filter(user=request.user, id__in=selected_ids)
        count = bookmarks_to_delete.count()
        bookmarks_to_delete.delete()
        messages.success(request, f"Successfully deleted {count} bookmark(s).")

    return _close_modal_and_refresh()
