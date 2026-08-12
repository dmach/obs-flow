import msgspec
from obs_flow_common.messages.core import ReviewDetail

class StagingResponse(msgspec.Struct):
    """Details of a staging batch, used for detail views and creation/edit responses."""
    id: int
    state: str
    creator: str | None = None
    title: str | None = None
    target_project: str | None = None
    pull_requests: list[str] = []
    embargo_date: str | None = None
    release_date: str | None = None


# Aliases for backward compatibility
StagingDetail = StagingResponse
StagingCreateResponse = StagingResponse
StagingEditResponse = StagingResponse


class StagingCreateRequest(msgspec.Struct):
    """Request to create a new staging batch."""
    title: str | None = None
    embargo_date: str | None = None
    release_date: str | None = None


class StagingEditRequest(msgspec.Struct):
    """Request to edit an existing staging batch."""
    id: int
    title: str | None = None
    embargo_date: str | None = None
    release_date: str | None = None


class StagingUpdatePullRequestsResponse(msgspec.Struct):
    """Response containing the updated list of pull requests in the staging batch."""
    id: int
    pull_requests: list[str]


# Aliases for backward compatibility
StagingAddResponse = StagingUpdatePullRequestsResponse
StagingRemoveResponse = StagingUpdatePullRequestsResponse


class StagingAddRequest(msgspec.Struct):
    """Request to add pull requests to a staging batch."""
    id: int
    pull_request_ids: list[str]
    allow_duplicates: bool = False


class StagingRemoveRequest(msgspec.Struct):
    """Request to remove pull requests from a staging batch."""
    id: int
    pull_request_ids: list[str]


# =====================================================================
# Staging Review Models
# =====================================================================

class StagingReviewShowRequest(msgspec.Struct):
    """Request to show review details for a staging batch."""
    staging_id: int
    reviewer: str | None = None


class StagingReviewShowResponse(msgspec.Struct):
    """Response containing review details for a staging batch."""
    staging_id: int
    reviews: list[ReviewDetail]


class StagingReviewActionResponse(msgspec.Struct):
    """Unified response containing the updated review state after an action on a staging batch."""
    staging_id: int
    review: ReviewDetail


class StagingReviewApproveRequest(msgspec.Struct):
    """Request to approve a staging batch review."""
    staging_id: int
    reviewer: str | None = None
    override: bool = False


class StagingReviewDeclineRequest(msgspec.Struct):
    """Request to decline a staging batch review."""
    staging_id: int
    message: str
    reviewer: str | None = None
    override: bool = False


class StagingReviewNeedInfoRequest(msgspec.Struct):
    """Request to put a staging batch review in needinfo state."""
    staging_id: int
    message: str
    reviewer: str | None = None
    override: bool = False


class StagingReviewClearNeedInfoRequest(msgspec.Struct):
    """Request to clear needinfo state on a staging batch."""
    staging_id: int
    message: str
    override: bool = False


class StagingReviewReopenRequest(msgspec.Struct):
    """Request to reopen a declined staging batch review."""
    staging_id: int
    message: str
    reviewer: str | None = None
    override: bool = False
