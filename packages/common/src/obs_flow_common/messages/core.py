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


class OrgDetail(msgspec.Struct):
    id: int
    name: str
    is_personal: bool
    user: str | None = None


class OrgListRequest(msgspec.Struct):
    pass


class OrgListResponse(msgspec.Struct):
    orgs: list[OrgDetail]


class OrgCreateRequest(msgspec.Struct):
    name: str
    user: str | None = None


class OrgCreateResponse(msgspec.Struct):
    org: OrgDetail


class ProjectDetail(msgspec.Struct):
    id: int
    name: str
    workflow_type: str
    org: str | None = None
    branch_name: str | None = None


class ProjectListRequest(msgspec.Struct):
    pass


class ProjectListResponse(msgspec.Struct):
    projects: list[ProjectDetail]


class ProjectCreateRequest(msgspec.Struct):
    name: str
    org: str | None = None
    branch_name: str | None = None
    workflow_type: str = "direct"


class ProjectCreateResponse(msgspec.Struct):
    project: ProjectDetail


class ProjectUpdateRequest(msgspec.Struct):
    name: str
    workflow_type: str | None = None


class ProjectUpdateResponse(msgspec.Struct):
    project: ProjectDetail


class PackageDetail(msgspec.Struct):
    id: int
    project: str
    name: str
    forked_from: str | None = None


class PackageListRequest(msgspec.Struct):
    project: str | None = None


class PackageListResponse(msgspec.Struct):
    packages: list[PackageDetail]


class PackageCreateRequest(msgspec.Struct):
    project: str
    name: str
    from_branch: str | None = None
    fork_from_project: str | None = None
    fork_from_package: str | None = None


class PackageCreateResponse(msgspec.Struct):
    package: PackageDetail
