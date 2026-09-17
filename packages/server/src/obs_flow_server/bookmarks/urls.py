from django.urls import path
import bookmarks.views as views

urlpatterns = [
    path("", views.bookmark_list, name="bookmark_list"),
    path("create/", views.bookmark_create, name="bookmark_create"),
    path("<int:pk>/edit/", views.bookmark_edit_inline, name="bookmark_edit_inline"),
    path("<int:pk>/cancel/", views.bookmark_cancel_edit, name="bookmark_cancel_edit"),
    path("delete/confirm/", views.bookmark_delete_confirm, name="bookmark_delete_confirm"),
    path("delete/", views.bookmark_delete_bulk, name="bookmark_delete_bulk"),
]
