from django.urls import path
from . import views

urlpatterns = [
    # Package-level git HTTP transport
    path("package/<str:project>/<str:package>", views.package_repo_root, name="git_package_root"),
    path("package/<str:project>/<str:package>/", views.package_repo_root, name="git_package_root_slash"),
    path("package/<str:project>/<str:package>/info/refs", views.package_info_refs, name="git_package_info_refs"),
    path("package/<str:project>/<str:package>/git-upload-pack", views.package_upload_pack, name="git_package_upload_pack"),
    path("package/<str:project>/<str:package>/git-receive-pack", views.package_receive_pack, name="git_package_receive_pack"),

    # Package-level Git LFS endpoints
    path("package/<str:project>/<str:package>/info/lfs/objects/batch", views.package_lfs_batch, name="git_package_lfs_batch"),
    path("package/<str:project>/<str:package>/info/lfs/objects/<str:oid>", views.package_lfs_object, name="git_package_lfs_object"),
    path("package/<str:project>/<str:package>/info/lfs/objects/verify", views.package_lfs_verify, name="git_package_lfs_verify"),

    # Project-level git HTTP transport
    path("project/<str:project>", views.project_repo_root, name="git_project_root"),
    path("project/<str:project>/", views.project_repo_root, name="git_project_root_slash"),
    path("project/<str:project>/info/refs", views.project_info_refs, name="git_project_info_refs"),
    path("project/<str:project>/git-upload-pack", views.project_upload_pack, name="git_project_upload_pack"),
    path("project/<str:project>/git-receive-pack", views.project_receive_pack, name="git_project_receive_pack"),

    # Project-level Git LFS endpoints
    path("project/<str:project>/info/lfs/objects/batch", views.project_lfs_batch, name="git_project_lfs_batch"),
    path("project/<str:project>/info/lfs/objects/<str:oid>", views.project_lfs_object, name="git_project_lfs_object"),
    path("project/<str:project>/info/lfs/objects/verify", views.project_lfs_verify, name="git_project_lfs_verify"),
]
