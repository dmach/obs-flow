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

from django.contrib import admin
from django.urls import path

import core.views as core_views
import pull_requests.views as pr_views
import staging.views as staging_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.home, name="home"),
    path("pull_requests/", pr_views.pr_list, name="pr_list"),
    path("pull_requests/<int:pr_id>/", pr_views.pr_detail, name="pr_detail"),
    path("staging/", staging_views.staging_list, name="staging_list"),
    path("staging/<int:batch_id>/", staging_views.staging_detail, name="staging_detail"),
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
]
