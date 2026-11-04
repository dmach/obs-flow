import msgspec
from asgiref.sync import sync_to_async
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from obs_flow_common.messages.reviews import (
    ReviewConfigDTO,
    ReviewConfigAddRequest,
    ReviewConfigRemoveRequest,
    ReviewConfigListRequest,
    ReviewConfigAddResponse,
    ReviewConfigRemoveResponse,
    ReviewConfigListResponse,
    ReviewScopeDTO,
    ReviewScopeListRequest,
    ReviewScopeListResponse,
    ReviewScopeAddRequest,
    ReviewScopeAddResponse,
    ReviewScopeRemoveRequest,
    ReviewScopeRemoveResponse,
    ReviewScopeUpdateRequest,
    ReviewScopeUpdateResponse,
    ReviewerDTO,
    PersonReviewerDTO,
    GroupReviewerDTO,
    DynamicRoleReviewerDTO,
)
from obs_flow_server.api import api

from accounts.models import User, Group
from core.models import Project
from reviews.models import ReviewConfig, ReviewScope


def parse_reviewer(reviewer_str: str) -> tuple[User | None, Group | None, str | None]:
    """
    Parses a reviewer string into (user, group, dynamic_role).
    Exactly one of them will be returned as non-None.
    """
    if reviewer_str.startswith("@"):
        group_name = reviewer_str[1:]
        group = Group.objects.get(name=group_name)
        return None, group, None
    elif reviewer_str.startswith("role:"):
        role_name = reviewer_str[len("role:"):]
        if role_name not in ReviewConfig.DynamicRole.values:
            raise ValueError(f"Invalid dynamic role: {role_name}")
        return None, None, role_name
    else:
        user = User.objects.get(username=reviewer_str)
        return user, None, None


def format_reviewer(config: ReviewConfig) -> str:
    """
    Formats a ReviewConfig's reviewer into a string identifier.
    """
    if config.reviewer_user:
        return config.reviewer_user.username
    elif config.reviewer_group:
        return f"@{config.reviewer_group.name}"
    elif config.dynamic_role:
        return f"role:{config.dynamic_role}"
    else:
        raise ValueError("Invalid review configuration: no reviewer set")


def get_review_config(project: Project, config_type: str, reviewer_str: str) -> ReviewConfig:
    """
    Finds an existing ReviewConfig by project, type, and reviewer string.
    """
    user, group, dynamic_role = parse_reviewer(reviewer_str)
    return ReviewConfig.objects.get(
        project=project,
        type=config_type,
        reviewer_user=user,
        reviewer_group=group,
        dynamic_role=dynamic_role,
    )


def build_reviewer_dto_from_fields(user: User | None, group: Group | None, dynamic_role: str | None) -> ReviewerDTO:
    """
    Converts reviewer fields into a ReviewerDTO message struct.
    """
    if user:
        return PersonReviewerDTO(
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
        )
    elif group:
        return GroupReviewerDTO(
            name=group.name,
            email=group.email,
        )
    elif dynamic_role:
        return DynamicRoleReviewerDTO(
            role=dynamic_role,
        )
    else:
        raise ValueError("Invalid reviewer: no user, group, or dynamic role set")


def build_reviewer_dto(config: ReviewConfig) -> ReviewerDTO:
    """
    Converts a ReviewConfig's reviewer into a ReviewerDTO message struct.
    """
    return build_reviewer_dto_from_fields(config.reviewer_user, config.reviewer_group, config.dynamic_role)


def build_review_config_dto(config: ReviewConfig) -> ReviewConfigDTO:
    """
    Converts a ReviewConfig instance to a ReviewConfigDTO message struct.
    """
    depends_on_list = [build_reviewer_dto(dep) for dep in config.depends_on.all()]
    return ReviewConfigDTO(
        id=config.id,
        project=config.project.name,
        type=config.type,
        reviewer=build_reviewer_dto(config),
        depends_on=depends_on_list,
    )


@api.post("/api/v1/review-config/add")
@sync_to_async
def add_review_config_endpoint(payload: ReviewConfigAddRequest):
    """
    Adds a review configuration for a project.
    """
    project = Project.objects.get(name=payload.project)

    # Validate type choice
    if payload.type not in ReviewConfig.ConfigType.values:
        raise ValueError(f"Invalid configuration type: {payload.type}")

    # Parse reviewer
    user, group, dynamic_role = parse_reviewer(payload.reviewer)

    with transaction.atomic():
        config, created = ReviewConfig.objects.get_or_create(
            project=project,
            type=payload.type,
            reviewer_user=user,
            reviewer_group=group,
            dynamic_role=dynamic_role,
        )

        if not created:
            raise ValueError(f"Review configuration for reviewer '{payload.reviewer}' with type '{payload.type}' already exists.")

        # Resolve depends_on
        resolved_dependencies = []
        for dep_str in payload.depends_on:
            dep_config = get_review_config(project, payload.type, dep_str)
            resolved_dependencies.append(dep_config)

        # Validate DAG / no circular dependencies
        config.validate_no_cycles(resolved_dependencies)

        config.depends_on.set(resolved_dependencies)

        # Return the response
        dto = build_review_config_dto(config)
        res = ReviewConfigAddResponse(data=dto)
        return msgspec.structs.asdict(res)


@api.post("/api/v1/review-config/remove")
@sync_to_async
def remove_review_config_endpoint(payload: ReviewConfigRemoveRequest):
    """
    Removes a review configuration for a project.
    """
    project = Project.objects.get(name=payload.project)

    # Validate type choice
    if payload.type not in ReviewConfig.ConfigType.values:
        raise ValueError(f"Invalid configuration type: {payload.type}")

    config = get_review_config(project, payload.type, payload.reviewer)

    # Convert to DTO before deleting
    dto = build_review_config_dto(config)
    config.delete()
    res = ReviewConfigRemoveResponse(data=dto)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/review-config/list")
@sync_to_async
def list_review_configs_endpoint(payload: ReviewConfigListRequest):
    """
    Lists review configurations for a project.
    """
    project = Project.objects.get(name=payload.project)

    qs = ReviewConfig.objects.filter(project=project)
    if payload.type is not None:
        # Validate type choice
        if payload.type not in ReviewConfig.ConfigType.values:
            raise ValueError(f"Invalid configuration type: {payload.type}")
        qs = qs.filter(type=payload.type)

    qs = qs.prefetch_related("depends_on")

    dtos = [build_review_config_dto(config) for config in qs]
    res = ReviewConfigListResponse(data=dtos)
    return msgspec.structs.asdict(res)


def build_review_scope_dto(scope: ReviewScope) -> ReviewScopeDTO:
    """Converts a ReviewScope instance to a ReviewScopeDTO message struct."""
    return ReviewScopeDTO(
        name=scope.name,
        include_globs=list(scope.include_globs or []),
        exclude_globs=list(scope.exclude_globs or []),
    )


@api.post("/api/v1/review-scope/list")
@sync_to_async
def list_review_scopes(payload: ReviewScopeListRequest):
    """Lists all review scopes, ordered by name."""
    scopes = ReviewScope.objects.all().order_by("name")
    dtos = [build_review_scope_dto(scope) for scope in scopes]
    res = ReviewScopeListResponse(scopes=dtos)
    return msgspec.structs.asdict(res)


@api.post("/api/v1/review-scope/add")
@sync_to_async
@transaction.atomic
def add_review_scope(payload: ReviewScopeAddRequest):
    """Adds a new review scope."""
    name = payload.name.strip()
    if not name:
        raise ValueError("Scope name must not be empty.")
    if name in ReviewScope.RESERVED_NAMES:
        raise ValueError(f"The '{name}' scope is reserved and cannot be created.")
    if not payload.include_globs:
        raise ValueError("A scope must have at least one include glob.")

    try:
        scope = ReviewScope.objects.create(
            name=name,
            include_globs=list(payload.include_globs),
            exclude_globs=list(payload.exclude_globs or []),
        )
    except IntegrityError:
        raise ValueError(f"A review scope named '{name}' already exists.")

    res = ReviewScopeAddResponse(scope=build_review_scope_dto(scope))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/review-scope/update")
@sync_to_async
@transaction.atomic
def update_review_scope(payload: ReviewScopeUpdateRequest):
    """Updates an existing review scope's globs. The name is the identifier; rename is not supported."""
    try:
        scope = ReviewScope.objects.get(name=payload.name)
    except ReviewScope.DoesNotExist:
        raise ValueError(f"Review scope '{payload.name}' does not exist.")

    if payload.include_globs is None and payload.exclude_globs is None:
        raise ValueError("Provide at least one of include_globs or exclude_globs to update.")

    if payload.include_globs is not None:
        if not payload.include_globs:
            raise ValueError("include_globs must not be empty.")
        scope.include_globs = list(payload.include_globs)
    if payload.exclude_globs is not None:
        scope.exclude_globs = list(payload.exclude_globs)

    scope.save()  # raises ValueError for reserved scopes (e.g. 'global')

    res = ReviewScopeUpdateResponse(scope=build_review_scope_dto(scope))
    return msgspec.structs.asdict(res)


@api.post("/api/v1/review-scope/remove")
@sync_to_async
@transaction.atomic
def remove_review_scope(payload: ReviewScopeRemoveRequest):
    """Removes a review scope by name."""
    try:
        scope = ReviewScope.objects.get(name=payload.name)
    except ReviewScope.DoesNotExist:
        return msgspec.structs.asdict(ReviewScopeRemoveResponse(success=False))

    try:
        scope.delete()  # raises ValueError for reserved scopes; ProtectedError if referenced
    except ProtectedError:
        raise ValueError(
            f"Review scope '{payload.name}' is referenced by existing review configs or reviews "
            "and cannot be removed."
        )

    return msgspec.structs.asdict(ReviewScopeRemoveResponse(success=True))
