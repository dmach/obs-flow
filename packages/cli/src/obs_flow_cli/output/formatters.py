from obs_flow_common.messages import (
    UserDTO,
    ReviewerDTO,
    PersonReviewerDTO,
    GroupReviewerDTO,
    DynamicRoleReviewerDTO,
)


def format_user_dto(user: UserDTO) -> str:
    parts = []
    if user.full_name:
        parts.append(user.full_name)
    if user.email:
        parts.append(f"<{user.email}>")
    
    if parts:
        return f"{user.username} ({' '.join(parts)})"
    return user.username


def format_group_reviewer_dto(reviewer: GroupReviewerDTO) -> str:
    if reviewer.email:
        return f"@{reviewer.name} (<{reviewer.email}>)"
    return f"@{reviewer.name}"


def format_dynamic_role_reviewer_dto(reviewer: DynamicRoleReviewerDTO) -> str:
    return f"role:{reviewer.role}"


def format_reviewer_dto(reviewer: ReviewerDTO) -> str:
    if isinstance(reviewer, PersonReviewerDTO):
        return format_user_dto(reviewer)
    elif isinstance(reviewer, GroupReviewerDTO):
        return format_group_reviewer_dto(reviewer)
    elif isinstance(reviewer, DynamicRoleReviewerDTO):
        return format_dynamic_role_reviewer_dto(reviewer)
    return str(reviewer)
