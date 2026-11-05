from django.urls import path
from . import views

urlpatterns = [
    # Package-level git HTTP transport
    path("package/<str:project>/<str:package>/info/refs", views.package_info_refs, name="git_package_info_refs"),
    path("package/<str:project>/<str:package>/git-upload-pack", views.package_upload_pack, name="git_package_upload_pack"),
    path("package/<str:project>/<str:package>/git-receive-pack", views.package_receive_pack, name="git_package_receive_pack"),

    # Project-level git HTTP transport
    path("project/<str:project>/info/refs", views.project_info_refs, name="git_project_info_refs"),
    path("project/<str:project>/git-upload-pack", views.project_upload_pack, name="git_project_upload_pack"),
    path("project/<str:project>/git-receive-pack", views.project_receive_pack, name="git_project_receive_pack"),
]
