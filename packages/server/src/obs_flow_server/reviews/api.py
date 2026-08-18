import msgspec
from asgiref.sync import sync_to_async

from obs_flow_common.messages.reviews import (
    ReviewConfigDTO,
    ReviewConfigAddRequest,
    ReviewConfigRemoveRequest,
    ReviewConfigListRequest,
    ReviewConfigAddResponse,
    ReviewConfigRemoveResponse,
    ReviewConfigListResponse,
)
from obs_flow_server.api import api

from accounts.models import User, Group
from core.models import Project
from reviews.models import ReviewConfig


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


def build_review_config_dto(config: ReviewConfig) -> ReviewConfigDTO:
    """
    Converts a ReviewConfig instance to a ReviewConfigDTO message struct.
    """
    depends_on_list = [format_reviewer(dep) for dep in config.depends_on.all()]
    return ReviewConfigDTO(
        id=config.id,
        project=config.project.name,
        type=config.type,
        reviewer=format_reviewer(config),
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
