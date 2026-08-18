import msgspec
from obs_flow_common.messages.core import UserDTO
from obs_flow_common.messages.reviews import ReviewDetail


class PRDetail(msgspec.Struct):
    """Details of a pull request."""
    id: str
    title: str | None
    state: str
    is_draft: bool
    is_mergeable: bool | None
    author: UserDTO
    latest_revision: int
    head_sha: str
    base_sha: str


class PRSyncRequest(msgspec.Struct):
    """Request to synchronize a pull request from Gitea."""
    owner: str
    repo: str
    number: int


class PRSyncResponse(msgspec.Struct):
    """Response containing the synchronized pull request details."""
    pull_request: PRDetail


class PRReviewShowRequest(msgspec.Struct):
    """Request to show review details for a pull request."""
    pull_request_id: str
    reviewer: str | None = None


class PRReviewShowResponse(msgspec.Struct):
    """Response containing review details for a pull request."""
    pull_request_id: str
    reviews: list[ReviewDetail]


class PRReviewActionResponse(msgspec.Struct):
    """Unified response containing the updated review state after an action."""
    pull_request_id: str
    review: ReviewDetail


class PRReviewApproveRequest(msgspec.Struct):
    """Request to approve a pull request review."""
    pull_request_id: str
    reviewer: str | None = None
    override: bool = False


class PRReviewDeclineRequest(msgspec.Struct):
    """Request to decline a pull request review."""
    pull_request_id: str
    message: str
    reviewer: str | None = None
    override: bool = False


class PRReviewNeedInfoRequest(msgspec.Struct):
    """Request to put a pull request review in needinfo state."""
    pull_request_id: str
    message: str
    reviewer: str | None = None
    override: bool = False


class PRReviewClearNeedInfoRequest(msgspec.Struct):
    """Request to clear needinfo state on a pull request."""
    pull_request_id: str
    message: str
    override: bool = False


class PRReviewReopenRequest(msgspec.Struct):
    """Request to reopen a declined pull request review."""
    pull_request_id: str
    message: str
    reviewer: str | None = None
    override: bool = False
