"""Client library functions for Pull Request Reviews.

This module provides functions to interact with the OBS Flow server's
RPC-like endpoints for managing pull request reviews.
"""

import msgspec
from obs_flow_common.messages import (
    PRReviewActionResponse,
    PRReviewApproveRequest,
    PRReviewClearNeedInfoRequest,
    PRReviewDeclineRequest,
    PRReviewNeedInfoRequest,
    PRReviewReopenRequest,
    PRReviewShowRequest,
    PRReviewShowResponse,
    ReviewConfigDTO,
    ReviewConfigAddRequest,
    ReviewConfigRemoveRequest,
    ReviewConfigListRequest,
    ReviewConfigAddResponse,
    ReviewConfigRemoveResponse,
    ReviewConfigListResponse,
    ReviewScopeListRequest,
    ReviewScopeListResponse,
    ReviewScopeAddRequest,
    ReviewScopeAddResponse,
    ReviewScopeRemoveRequest,
    ReviewScopeRemoveResponse,
    ReviewScopeUpdateRequest,
    ReviewScopeUpdateResponse,
)

from obs_flow_client.connection import Connection


def review_config_add(conn: Connection, req: ReviewConfigAddRequest) -> ReviewConfigAddResponse:
    """Adds a review configuration for a project."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-config/add", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewConfigAddResponse)


def review_config_remove(conn: Connection, req: ReviewConfigRemoveRequest) -> ReviewConfigRemoveResponse:
    """Removes a review configuration for a project."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-config/remove", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewConfigRemoveResponse)


def review_config_list(conn: Connection, req: ReviewConfigListRequest) -> ReviewConfigListResponse:
    """Lists review configurations for a project."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-config/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewConfigListResponse)


def pr_review_show(conn: Connection, req: PRReviewShowRequest) -> PRReviewShowResponse:
    """Retrieves review details for a pull request."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/show", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewShowResponse)


def pr_review_approve(conn: Connection, req: PRReviewApproveRequest) -> PRReviewActionResponse:
    """Approves a pull request review."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/approve", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def pr_review_decline(conn: Connection, req: PRReviewDeclineRequest) -> PRReviewActionResponse:
    """Declines a pull request review."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/decline", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def pr_review_needinfo(conn: Connection, req: PRReviewNeedInfoRequest) -> PRReviewActionResponse:
    """Puts a pull request review in needinfo state."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/needinfo", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def pr_review_clear_needinfo(
    conn: Connection, req: PRReviewClearNeedInfoRequest
) -> PRReviewActionResponse:
    """Clears needinfo state on a pull request."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/clear_needinfo", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def pr_review_reopen(conn: Connection, req: PRReviewReopenRequest) -> PRReviewActionResponse:
    """Reopens a declined pull request review."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/reopen", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def review_scope_list(conn: Connection, req: ReviewScopeListRequest) -> ReviewScopeListResponse:
    """Lists all review scopes."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-scope/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewScopeListResponse)


def review_scope_add(conn: Connection, req: ReviewScopeAddRequest) -> ReviewScopeAddResponse:
    """Adds a new review scope."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-scope/add", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewScopeAddResponse)


def review_scope_update(conn: Connection, req: ReviewScopeUpdateRequest) -> ReviewScopeUpdateResponse:
    """Update an existing review scope's globs."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-scope/update", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewScopeUpdateResponse)


def review_scope_remove(conn: Connection, req: ReviewScopeRemoveRequest) -> ReviewScopeRemoveResponse:
    """Removes a review scope by name."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-scope/remove", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewScopeRemoveResponse)
