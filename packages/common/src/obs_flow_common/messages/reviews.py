import msgspec


class ReviewConfigDTO(msgspec.Struct):
    """
    DTO (Data Transfer Object) representing a serialized review configuration.

    Attributes:
        id: The database ID of the configuration.
        project: The name of the project.
        type: The type of configuration (project, package, staging).
        reviewer: The reviewer identifier (e.g., username, @group, role:role_name).
        depends_on: List of reviewer identifiers this configuration depends on.
    """
    id: int
    project: str
    type: str
    reviewer: str
    depends_on: list[str]


class ReviewConfigAddRequest(msgspec.Struct):
    """
    Request payload to add a new review configuration.

    Attributes:
        project: The name of the project.
        type: The type of configuration (project, package, staging).
        reviewer: The reviewer identifier (e.g., username, @group, role:role_name).
        depends_on: List of reviewer identifiers this configuration depends on.
    """
    project: str
    type: str
    reviewer: str
    depends_on: list[str]


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
