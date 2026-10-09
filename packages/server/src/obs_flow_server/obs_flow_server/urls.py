"""
URL configuration for obs_flow_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path

import core.views as core_views
import pull_requests.views as pr_views
import staging.views as staging_views

urlpatterns = [
    path("", core_views.home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("bookmarks/", include("bookmarks.urls")),
    path("git-mappings/", core_views.git_mapping_list, name="git_mapping_list"),
    path("pull-requests/", pr_views.pr_list, name="pr_list"),
    path("pull-requests/<int:pr_id>/", pr_views.pr_detail, name="pr_detail"),
    path("pull-requests/<int:pr_id>/draft-status/", pr_views.pr_draft_status, name="pr_draft_status"),
    path("pull-requests/<int:pr_id>/ready-for-review/", pr_views.pr_ready_for_review, name="pr_ready_for_review"),
    path("pull-requests/<int:pr_id>/convert-to-draft/", pr_views.pr_convert_to_draft, name="pr_convert_to_draft"),
    path("staging/", staging_views.staging_list, name="staging_list"),
    path("staging/<int:batch_id>/", staging_views.staging_detail, name="staging_detail"),
    path("staging/<int:batch_id>/draft-status/", staging_views.staging_draft_status, name="staging_draft_status"),
    path("staging/<int:batch_id>/ready-for-review/", staging_views.staging_ready_for_review, name="staging_ready_for_review"),
    path("staging/<int:batch_id>/convert-to-draft/", staging_views.staging_convert_to_draft, name="staging_convert_to_draft"),
    path(
        "staging/<int:batch_id>/edit-date-form/<str:date_type>/",
        staging_views.staging_edit_date_form,
        name="staging_edit_date_form",
    ),
    path(
        "staging/<int:batch_id>/edit-date/<str:date_type>/", staging_views.staging_edit_date, name="staging_edit_date"
    ),
    path(
        "staging/<int:batch_id>/date-display/<str:date_type>/",
        staging_views.staging_date_display,
        name="staging_date_display",
    ),
    path(
        "staging/ui/modal/select-batch/",
        staging_views.staging_ui_modal_select_batch,
        name="staging_ui_modal_select_batch",
    ),
    path(
        "staging/ui/modal/confirm-add/",
        staging_views.staging_ui_modal_confirm_add,
        name="staging_ui_modal_confirm_add",
    ),
]
