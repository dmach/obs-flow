import msgspec
from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Q

from obs_flow_common.messages import (
    OrgDetail,
    OrgListRequest,
    OrgListResponse,
    OrgCreateRequest,
    OrgCreateResponse,
    ProjectDetail,
    ProjectListRequest,
    ProjectListResponse,
    ProjectShowRequest,
    ProjectShowResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectUpdateRequest,
    ProjectUpdateResponse,
    PackageDetail,
    PackageListRequest,
    PackageListResponse,
    PackageShowRequest,
    PackageShowResponse,
    PackageCreateRequest,
    PackageCreateResponse,
    CommentDTO,
    CommentAddRequest,
    CommentAddResponse,
    CommentListRequest,
    CommentListResponse,
)
from obs_flow_server.api import api
from accounts.models import User
from core.models import Project, Package, Org, Comment


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
    if payload.user:
        user_obj, _ = User.objects.get_or_create(
            username=payload.user,
            defaults={"username_lower": payload.user.lower(), "account_type": User.AccountType.HUMAN},
        )
        org, _ = Org.objects.get_or_create(
            user=user_obj,
            defaults={"name": payload.name},
        )
    else:
        org, _ = Org.objects.get_or_create(
            name=payload.name,
        )
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
    if payload.name:
        projects = projects.filter(name__icontains=payload.name)
    if payload.org:
        projects = projects.filter(org__name__icontains=payload.org)
    if payload.workflow_type:
        projects = projects.filter(workflow_type=payload.workflow_type)
    details = [project_to_detail(p) for p in projects]
    res = ProjectListResponse(projects=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/project/show")
@sync_to_async
def show_project(payload: ProjectShowRequest):
    try:
        project = Project.objects.select_related("org").get(name=payload.name)
    except Project.DoesNotExist:
        raise ValueError(f"Project '{payload.name}' does not exist")
    res = ProjectShowResponse(project=project_to_detail(project))
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
        raise ValueError(f"Invalid workflow type: {workflow_type}")

    project, created = Project.objects.get_or_create(
        name=payload.name,
        defaults={
            "org": org_obj,
            "branch_name": payload.branch_name,
            "workflow_type": workflow_type,
        },
    )
    if created and project.org:
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
        qs = qs.filter(project__name__icontains=payload.project)
    if payload.name:
        qs = qs.filter(name__icontains=payload.name)
    details = [package_to_detail(pkg) for pkg in qs]
    res = PackageListResponse(packages=details)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/package/show")
@sync_to_async
def show_package(payload: PackageShowRequest):
    try:
        package = Package.objects.select_related("project", "forked_from", "forked_from__project").get(
            project__name=payload.project, name=payload.name
        )
    except Package.DoesNotExist:
        raise ValueError(f"Package '{payload.project}/{payload.name}' does not exist")
    res = PackageShowResponse(package=package_to_detail(package))
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

    package, created = Package.objects.get_or_create(
        project=project,
        name=payload.name,
        defaults={"forked_from": forked_from},
    )

    if created and project.org:
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


def _resolve_comment_target(target_type: str, target_id: str):
    target_type = target_type.lower().strip()
    if target_type in ("pull_request", "pr"):
        from pull_requests.models import PullRequest
        if "#" in target_id:
            repo, num_str = target_id.rsplit("#", 1)
            num = int(num_str)
            parts = repo.split("/")
            if len(parts) == 2:
                owner_or_proj, pkg_name = parts[0], parts[1]
                pr = PullRequest.objects.filter(
                    Q(project__org__name=owner_or_proj) | Q(project__name=owner_or_proj),
                    package__name=pkg_name,
                    number=num,
                ).first()
                if pr:
                    return pr
                return PullRequest.objects.get(project__name=owner_or_proj, package__name=pkg_name, number=num)
            else:
                return PullRequest.objects.get(
                    Q(project__org__name=repo) | Q(project__name=repo),
                    package__isnull=True,
                    number=num,
                )
        elif target_id.isdigit():
            pr = PullRequest.objects.filter(id=int(target_id)).first()
            if pr:
                return pr
            return PullRequest.objects.get(number=int(target_id))
        else:
            raise ValueError(f"Invalid pull request identifier: '{target_id}'")
    elif target_type in ("staging_batch", "staging", "batch"):
        from staging.models import StagingBatch
        if target_id.isdigit():
            return StagingBatch.objects.get(id=int(target_id))
        else:
            raise ValueError(f"Invalid staging batch identifier: '{target_id}'")
    else:
        raise ValueError(f"Unsupported comment target_type: '{target_type}'")


def comment_to_dto(c: Comment) -> CommentDTO:
    is_pr = c.content_type.model == "pullrequest"
    is_thread = c.content_type.model == "reviewthread"
    target_type = "pull_request" if (is_pr or is_thread) else "staging_batch"
    revision_id = None
    if is_thread and c.content_object:
        thread = c.content_object
        target_id = thread.pull_request.formatted_id
        revision_id = thread.original_revision_id
        path = thread.path
        line_number = thread.line_number
    elif is_pr and hasattr(c.content_object, "formatted_id"):
        target_id = c.content_object.formatted_id
        path = c.path
        line_number = c.line_number
    else:
        target_id = str(c.object_id)
        path = c.path
        line_number = c.line_number

    return CommentDTO(
        id=c.id,
        target_type=target_type,
        target_id=target_id,
        author=c.author.username,
        body=c.body,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
        path=path,
        line_number=line_number,
        revision_id=revision_id,
    )


@api.post("/api/v1/comment/add")
@sync_to_async
@transaction.atomic
def add_comment(payload: CommentAddRequest):
    target = _resolve_comment_target(payload.target_type, payload.target_id)
    user, _ = User.objects.get_or_create(
        username=payload.author,
        defaults={"username_lower": payload.author.lower(), "account_type": User.AccountType.HUMAN},
    )

    if target.__class__.__name__ == "PullRequest" and payload.path and payload.line_number:
        from pull_requests.models import ReviewThread
        if payload.revision_id:
            rev = target.revisions.filter(id=payload.revision_id).first() or target.revisions.filter(revision_number=payload.revision_id).first()
        else:
            rev = target.revisions.order_by("-revision_number").first()
        if not rev:
            raise ValueError(f"No revision found for pull request {target.id}")

        thread = target.review_threads.filter(path=payload.path, line_number=payload.line_number, is_resolved=False).first()
        if not thread:
            thread = ReviewThread.objects.create(
                pull_request=target,
                original_revision=rev,
                original_commit_sha=rev.head_sha,
                path=payload.path,
                line_number=payload.line_number,
            )
        target = thread

    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(target)
    comment = Comment.objects.create(
        content_type=ct,
        object_id=str(target.id),
        author=user,
        body=payload.body.strip(),
        path=payload.path,
        line_number=payload.line_number,
    )
    res = CommentAddResponse(comment=comment_to_dto(comment))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/comment/list")
@sync_to_async
def list_comments(payload: CommentListRequest):
    target = _resolve_comment_target(payload.target_type, payload.target_id)
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(target)
    comments = list(Comment.objects.filter(content_type=ct, object_id=str(target.id)).select_related("author"))
    if target.__class__.__name__ == "PullRequest":
        from pull_requests.models import ReviewThread
        thread_ct = ContentType.objects.get_for_model(ReviewThread)
        thread_ids = list(target.review_threads.values_list("id", flat=True))
        if thread_ids:
            thread_comments = list(Comment.objects.filter(content_type=thread_ct, object_id__in=[str(tid) for tid in thread_ids]).select_related("author"))
            comments.extend(thread_comments)
    comments.sort(key=lambda c: c.created_at)
    dtos = [comment_to_dto(c) for c in comments]
    res = CommentListResponse(comments=dtos)
    return msgspec.structs.asdict(res)

