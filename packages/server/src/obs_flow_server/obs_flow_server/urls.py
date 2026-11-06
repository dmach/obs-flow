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

PR_ROUTES = [
    ("", pr_views.pr_detail, "pr_detail"),
    ("draft-status/", pr_views.pr_draft_status, "pr_draft_status"),
    ("ready-for-review/", pr_views.pr_ready_for_review, "pr_ready_for_review"),
    ("cancel-timeout/", pr_views.pr_cancel_timeout, "pr_cancel_timeout"),
    ("convert-to-draft/", pr_views.pr_convert_to_draft, "pr_convert_to_draft"),
    ("merge/", pr_views.pr_merge_action, "pr_merge_action"),
]

# PR routes exist twice under the same name; reverse() picks by kwargs
# (project_name, number) for project PRs or (project_name, package_name, number) for package PRs.
pr_urlpatterns = [
    path(f"{prefix}pull-requests/<int:number>/{suffix}", view, name=name)
    for suffix, view, name in PR_ROUTES
    for prefix in ("projects/<str:project_name>/", "packages/<str:project_name>/<str:package_name>/")
]

urlpatterns = [
    path("", core_views.home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("bookmarks/", include("bookmarks.urls")),
    path("projects/", core_views.project_list, name="project_list"),
    path("projects/<str:project_name>/", core_views.project_detail, name="project_detail"),
    path("projects/<str:project_name>/pull-requests/", pr_views.project_pr_list, name="project_pr_list"),
    path("projects/<str:project_name>/staging/", staging_views.project_staging_list, name="project_staging_list"),
    path("packages/", core_views.package_list, name="package_list"),
    path("packages/<str:project_name>/<str:package_name>/", core_views.package_detail, name="package_detail"),
    path("packages/<str:project_name>/<str:package_name>/pull-requests/", pr_views.package_pr_list, name="package_pr_list"),
    path("pull-requests/", pr_views.pr_list, name="pr_list"),
    *pr_urlpatterns,
    path("pull-requests/bulk-merge/", pr_views.pr_bulk_merge, name="pr_bulk_merge"),
    path("pull-requests/ui/modal/check-merge/", pr_views.pr_ui_modal_check_merge, name="pr_ui_modal_check_merge"),
    path("pull-requests/ui/modal/execute-merge/", pr_views.pr_ui_modal_execute_merge, name="pr_ui_modal_execute_merge"),
    path("staging/", staging_views.staging_list, name="staging_list"),
    path("staging/<int:batch_id>/", staging_views.staging_detail, name="staging_detail"),
    path("staging/<int:batch_id>/draft-status/", staging_views.staging_draft_status, name="staging_draft_status"),
    path("staging/<int:batch_id>/ready-for-review/", staging_views.staging_ready_for_review, name="staging_ready_for_review"),
    path("staging/<int:batch_id>/cancel-timeout/", staging_views.staging_cancel_timeout, name="staging_cancel_timeout"),
    path("staging/<int:batch_id>/convert-to-draft/", staging_views.staging_convert_to_draft, name="staging_convert_to_draft"),
    path("staging/<int:batch_id>/merge/", staging_views.staging_merge_action, name="staging_merge_action"),
    path("staging/bulk-merge/", staging_views.staging_bulk_merge, name="staging_bulk_merge"),
    path("staging/ui/modal/check-merge/", staging_views.staging_ui_modal_check_merge, name="staging_ui_modal_check_merge"),
    path("staging/ui/modal/execute-merge/", staging_views.staging_ui_modal_execute_merge, name="staging_ui_modal_execute_merge"),
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
    path("", include("git_transport.urls")),
]
