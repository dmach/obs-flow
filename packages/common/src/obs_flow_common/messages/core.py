import msgspec


class UserDTO(msgspec.Struct):
    """
    DTO (Data Transfer Object) representing a serialized user.
    """
    username: str
    full_name: str | None
    email: str | None
    is_active: bool


class GitMappingDetail(msgspec.Struct):
    id: int
    owner: str
    repo: str
    branch: str
    project: str | None
    package: str | None


class GitMappingListRequest(msgspec.Struct):
    pass


class GitMappingListResponse(msgspec.Struct):
    mappings: list[GitMappingDetail]


class GitMappingAddRequest(msgspec.Struct):
    owner: str
    repo: str
    branch: str
    project: str | None = None
    package: str | None = None


class GitMappingAddResponse(msgspec.Struct):
    mapping: GitMappingDetail


class GitMappingRemoveRequest(msgspec.Struct):
    id: int


class GitMappingRemoveResponse(msgspec.Struct):
    success: bool


class GitMappingEditRequest(msgspec.Struct):
    id: int
    owner: str | None = None
    repo: str | None = None
    branch: str | None = None
    project: str | None = None
    package: str | None = None


class GitMappingEditResponse(msgspec.Struct):
    mapping: GitMappingDetail
