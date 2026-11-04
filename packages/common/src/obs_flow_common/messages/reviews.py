import msgspec
from obs_flow_common.messages.core import UserDTO


class ReviewerDataBase(msgspec.Struct, tag=True):
    """Base class for reviewer details."""
    pass


class PersonReviewerDTO(ReviewerDataBase, UserDTO, tag="person"):
    pass


class GroupReviewerDTO(ReviewerDataBase, tag="group"):
    name: str
    email: str | None


class DynamicRoleReviewerDTO(ReviewerDataBase, tag="role"):
    role: str


ReviewerDTO = PersonReviewerDTO | GroupReviewerDTO | DynamicRoleReviewerDTO


class ReviewDetail(msgspec.Struct):
    """Details of an individual review."""
    reviewer: ReviewerDTO
    state: str
    actor: UserDTO | None = None
    when: str | None = None
    why: str | None = None
    scope: str = "global"
    is_inherited: bool = False


class ReviewScopeDTO(msgspec.Struct):
    """DTO representing a globally-defined review scope."""
    name: str
    include_globs: list[str]
    exclude_globs: list[str]


class ReviewScopeListRequest(msgspec.Struct):
    """Request payload to list all review scopes."""
    pass


class ReviewScopeListResponse(msgspec.Struct):
    """Response payload containing the list of review scopes."""
    scopes: list[ReviewScopeDTO]


class ReviewScopeAddRequest(msgspec.Struct):
    """
    Request payload to add a new review scope.

    Attributes:
        name: The unique name of the scope.
        include_globs: Glob patterns; a file is in-scope if it matches at least one.
        exclude_globs: Glob patterns; a file is out-of-scope if it matches any.
    """
    name: str
    include_globs: list[str]
    exclude_globs: list[str] = []


class ReviewScopeAddResponse(msgspec.Struct):
    """Response payload for adding a review scope."""
    scope: ReviewScopeDTO


class ReviewScopeRemoveRequest(msgspec.Struct):
    """
    Request payload to remove a review scope.

    Attributes:
        name: The name of the scope to remove.
    """
    name: str


class ReviewScopeRemoveResponse(msgspec.Struct):
    """Response payload for removing a review scope."""
    success: bool


class ReviewScopeUpdateRequest(msgspec.Struct):
    """
    Request payload to update an existing review scope.

    Attributes:
        name: The name of the scope to update (identifier).
        include_globs: New include globs (replaces existing). Optional.
        exclude_globs: New exclude globs (replaces existing). Optional.
    """
    name: str
    include_globs: list[str] | None = None
    exclude_globs: list[str] | None = None


class ReviewScopeUpdateResponse(msgspec.Struct):
    """Response payload for updating a review scope."""
    scope: ReviewScopeDTO


class ReviewConfigDTO(msgspec.Struct):
    """
    DTO (Data Transfer Object) representing a serialized review configuration.

    Attributes:
        id: The database ID of the configuration.
        project: The name of the project.
        type: The type of configuration (project, package, staging).
        reviewer: The reviewer details.
        depends_on: List of reviewer details this configuration depends on.
        scope: The name of the review scope.
    """
    id: int
    project: str
    type: str
    reviewer: ReviewerDTO
    depends_on: list[ReviewerDTO]
    scope: str = "global"


class ReviewConfigAddRequest(msgspec.Struct):
    """
    Request payload to add a new review configuration.

    Attributes:
        project: The name of the project.
        type: The type of configuration (project, package, staging).
        reviewer: The reviewer identifier (e.g., username, @group, role:role_name).
        depends_on: List of reviewer identifiers this configuration depends on.
        scope: The name of the review scope (required; callers must always specify it).
    """
    project: str
    type: str
    reviewer: str
    depends_on: list[str]
    scope: str


class ReviewConfigRemoveRequest(msgspec.Struct):
    """
    Request payload to remove a review configuration.

    Attributes:
        project: The name of the project.
        type: The type of configuration (project, package, staging).
        reviewer: Reviewer identifier to remove by reviewer name.
    """
    project: str
    type: str
    reviewer: str


class ReviewConfigListRequest(msgspec.Struct):
    """
    Request payload to list review configurations.

    Attributes:
        project: The name of the project.
        type: Optional type to filter configurations (project, package, staging).
    """
    project: str
    type: str | None = None


class ReviewConfigAddResponse(msgspec.Struct):
    """
    Response payload for adding a review configuration.
    """
    data: ReviewConfigDTO


class ReviewConfigRemoveResponse(msgspec.Struct):
    """
    Response payload for removing a review configuration.
    """
    data: ReviewConfigDTO


class ReviewConfigListResponse(msgspec.Struct):
    """
    Response payload containing the list of review configurations.
    """
    data: list[ReviewConfigDTO]
