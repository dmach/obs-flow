"""
Shared helpers for HTMX views.
"""

from django.http import HttpResponse


def close_modal_and_refresh() -> HttpResponse:
    """
    Close the htmx modal and reload the page.

    The reload re-renders the list with fresh data and unchecked checkboxes, and
    displays the queued django.contrib.messages as toasts - no JavaScript needed.
    """
    response = HttpResponse("")
    response["HX-Refresh"] = "true"
    return response
