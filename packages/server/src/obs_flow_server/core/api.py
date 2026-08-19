import msgspec
from asgiref.sync import sync_to_async
from django.db import transaction
from django_bolt import BoltAPI

from obs_flow_common.messages import (
    GitMappingDetail,
    GitMappingListRequest,
    GitMappingListResponse,
    GitMappingAddRequest,
    GitMappingAddResponse,
    GitMappingRemoveRequest,
    GitMappingRemoveResponse,
    GitMappingEditRequest,
    GitMappingEditResponse,
)
from obs_flow_server.api import api
from core.models import GitMapping, Project, Package


def mapping_to_detail(mapping: GitMapping) -> GitMappingDetail:
    return GitMappingDetail(
        id=mapping.id,
        owner=mapping.owner,
        repo=mapping.repo,
        branch=mapping.branch,
        project=mapping.project.name if mapping.project else (mapping.package.project.name if mapping.package else None),
        package=mapping.package.name if mapping.package else None,
    )


@api.post("/api/v1/git-mapping/list")
@sync_to_async
def list_git_mappings(payload: GitMappingListRequest):
    mappings = GitMapping.objects.select_related("project", "package").all()
    details = [mapping_to_detail(m) for m in mappings]
    res = GitMappingListResponse(mappings=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/git-mapping/add")
@sync_to_async
@transaction.atomic
def add_git_mapping(payload: GitMappingAddRequest):
    if not payload.project and not payload.package:
        raise ValueError("Either project or package must be specified")

    project_obj = None
    package_obj = None

    if payload.package:
        if not payload.project:
            raise ValueError("Project must be specified when mapping to a package")
        try:
            project_obj = Project.objects.get(name=payload.project)
        except Project.DoesNotExist:
            raise ValueError(f"Project '{payload.project}' does not exist")
        package_obj, _ = Package.objects.get_or_create(project=project_obj, name=payload.package)
    else:
        project_obj, _ = Project.objects.get_or_create(name=payload.project)

    mapping = GitMapping.objects.create(
        owner=payload.owner,
        repo=payload.repo,
        branch=payload.branch,
        project=project_obj if not package_obj else None,
        package=package_obj,
    )

    res = GitMappingAddResponse(mapping=mapping_to_detail(mapping))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/git-mapping/remove")
@sync_to_async
@transaction.atomic
def remove_git_mapping(payload: GitMappingRemoveRequest):
    try:
        mapping = GitMapping.objects.get(id=payload.id)
        mapping.delete()
        success = True
    except GitMapping.DoesNotExist:
        success = False

    res = GitMappingRemoveResponse(success=success)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/git-mapping/edit")
@sync_to_async
@transaction.atomic
def edit_git_mapping(payload: GitMappingEditRequest):
    try:
        mapping = GitMapping.objects.get(id=payload.id)
    except GitMapping.DoesNotExist:
        raise ValueError(f"GitMapping with ID {payload.id} does not exist")

    if payload.owner is not None:
        mapping.owner = payload.owner
    if payload.repo is not None:
        mapping.repo = payload.repo
    if payload.branch is not None:
        mapping.branch = payload.branch

    # If project or package is being updated
    if payload.project is not None or payload.package is not None:
        # Determine final project and package names
        proj_name = payload.project if payload.project is not None else (mapping.project.name if mapping.project else (mapping.package.project.name if mapping.package else None))
        pkg_name = payload.package if payload.package is not None else (mapping.package.name if mapping.package else None)

        if not proj_name and not pkg_name:
            raise ValueError("Either project or package must be specified")

        project_obj = None
        package_obj = None

        if pkg_name:
            if not proj_name:
                raise ValueError("Project must be specified when mapping to a package")
            try:
                project_obj = Project.objects.get(name=proj_name)
            except Project.DoesNotExist:
                raise ValueError(f"Project '{proj_name}' does not exist")
            package_obj, _ = Package.objects.get_or_create(project=project_obj, name=pkg_name)
        else:
            project_obj, _ = Project.objects.get_or_create(name=proj_name)

        mapping.project = project_obj if not package_obj else None
        mapping.package = package_obj

    mapping.save()
    res = GitMappingEditResponse(mapping=mapping_to_detail(mapping))
    return msgspec.structs.asdict(res)
