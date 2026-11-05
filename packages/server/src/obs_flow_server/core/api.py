import msgspec
from asgiref.sync import sync_to_async
from django.db import transaction
from django_bolt import BoltAPI

from obs_flow_common.messages import (
    OrgDetail,
    OrgListRequest,
    OrgListResponse,
    OrgCreateRequest,
    OrgCreateResponse,
    ProjectDetail,
    ProjectListRequest,
    ProjectListResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectUpdateRequest,
    ProjectUpdateResponse,
    PackageDetail,
    PackageListRequest,
    PackageListResponse,
    PackageCreateRequest,
    PackageCreateResponse,
)
from obs_flow_server.api import api
from accounts.models import User
from core.models import Project, Package, Org


def org_to_detail(org: Org) -> OrgDetail:
    return OrgDetail(
        id=org.id,
        name=org.name,
        is_personal=org.is_personal,
        user=org.user.username if org.user else None,
    )


@api.post("/api/v1/org/list")
@sync_to_async
def list_orgs(payload: OrgListRequest):
    orgs = Org.objects.all().order_by("name")
    details = [org_to_detail(o) for o in orgs]
    res = OrgListResponse(orgs=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/org/create")
@sync_to_async
@transaction.atomic
def create_org(payload: OrgCreateRequest):
    user_obj = None
    if payload.user:
        try:
            user_obj = User.objects.get(username=payload.user)
        except User.DoesNotExist:
            raise ValueError(f"User '{payload.user}' does not exist")
    org = Org.objects.create(name=payload.name, user=user_obj)
    res = OrgCreateResponse(org=org_to_detail(org))
    return msgspec.structs.asdict(res)


def project_to_detail(project: Project) -> ProjectDetail:
    return ProjectDetail(
        id=project.id,
        name=project.name,
        workflow_type=project.workflow_type,
        org=project.org.name if project.org else None,
        branch_name=project.branch_name,
    )


@api.post("/api/v1/project/list")
@sync_to_async
def list_projects(payload: ProjectListRequest):
    projects = Project.objects.select_related("org").all().order_by("name")
    details = [project_to_detail(p) for p in projects]
    res = ProjectListResponse(projects=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/project/create")
@sync_to_async
@transaction.atomic
def create_project(payload: ProjectCreateRequest):
    org_obj = None
    if payload.org:
        try:
            org_obj = Org.objects.get(name=payload.org)
        except Org.DoesNotExist:
            raise ValueError(f"Org '{payload.org}' does not exist")

    workflow_type = payload.workflow_type or Project.WorkflowType.DIRECT
    if workflow_type not in Project.WorkflowType.values:
        raise ValueError(f"Invalid workflow type: {payload.workflow_type}")

    project = Project.objects.create(
        name=payload.name,
        org=org_obj,
        branch_name=payload.branch_name,
        workflow_type=workflow_type,
    )
    if project.org:
        from core.git_forge import ensure_git_repo
        ensure_git_repo(project.org.name, initial_branch=project.branch_name)

    res = ProjectCreateResponse(project=project_to_detail(project))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/project/update")
@sync_to_async
@transaction.atomic
def update_project(payload: ProjectUpdateRequest):
    try:
        project = Project.objects.get(name=payload.name)
    except Project.DoesNotExist:
        raise ValueError(f"Project '{payload.name}' does not exist")

    if payload.workflow_type is not None:
        if payload.workflow_type not in Project.WorkflowType.values:
            raise ValueError(f"Invalid workflow type: {payload.workflow_type}")
        project.workflow_type = payload.workflow_type
        project.save()

    res = ProjectUpdateResponse(project=project_to_detail(project))
    return msgspec.structs.asdict(res)


def package_to_detail(package: Package) -> PackageDetail:
    return PackageDetail(
        id=package.id,
        project=package.project.name,
        name=package.name,
        forked_from=str(package.forked_from) if package.forked_from else None,
    )


@api.post("/api/v1/package/list")
@sync_to_async
def list_packages(payload: PackageListRequest):
    qs = Package.objects.select_related("project", "forked_from", "forked_from__project").all().order_by("name")
    if payload.project:
        qs = qs.filter(project__name=payload.project)
    details = [package_to_detail(pkg) for pkg in qs]
    res = PackageListResponse(packages=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/package/create")
@sync_to_async
@transaction.atomic
def create_package(payload: PackageCreateRequest):
    try:
        project = Project.objects.get(name=payload.project)
    except Project.DoesNotExist:
        raise ValueError(f"Project '{payload.project}' does not exist")

    forked_from = None
    if payload.fork_from_project and payload.fork_from_package:
        try:
            forked_from = Package.objects.get(
                project__name=payload.fork_from_project,
                name=payload.fork_from_package,
            )
        except Package.DoesNotExist:
            raise ValueError(
                f"Source package '{payload.fork_from_project}/{payload.fork_from_package}' not found to fork"
            )

    package = Package.objects.create(
        project=project,
        name=payload.name,
        forked_from=forked_from,
    )

    if project.org:
        from core.git_forge import ensure_git_repo, fork_git_repo
        if forked_from and forked_from.project.org:
            fork_git_repo(
                source_org=forked_from.project.org.name,
                source_package=forked_from.name,
                target_org=project.org.name,
                target_package=package.name,
                branch=project.branch_name,
            )
        else:
            ensure_git_repo(project.org.name, package.name, initial_branch=project.branch_name)

    res = PackageCreateResponse(package=package_to_detail(package))
    return msgspec.structs.asdict(res)
