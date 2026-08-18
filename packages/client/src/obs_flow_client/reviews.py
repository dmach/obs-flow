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
)

from obs_flow_client.connection import Connection


def add_review_config(conn: Connection, req: ReviewConfigAddRequest) -> ReviewConfigAddResponse:
    """Adds a review configuration for a project."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-config/add", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewConfigAddResponse)


def remove_review_config(conn: Connection, req: ReviewConfigRemoveRequest) -> ReviewConfigRemoveResponse:
    """Removes a review configuration for a project."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-config/remove", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewConfigRemoveResponse)


def list_review_configs(conn: Connection, req: ReviewConfigListRequest) -> ReviewConfigListResponse:
    """Lists review configurations for a project."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/review-config/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ReviewConfigListResponse)


def show_review(conn: Connection, req: PRReviewShowRequest) -> PRReviewShowResponse:
    """Retrieves review details for a pull request."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/show", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewShowResponse)


def approve_review(conn: Connection, req: PRReviewApproveRequest) -> PRReviewActionResponse:
    """Approves a pull request review."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/approve", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def decline_review(conn: Connection, req: PRReviewDeclineRequest) -> PRReviewActionResponse:
    """Declines a pull request review."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/decline", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def needinfo_review(conn: Connection, req: PRReviewNeedInfoRequest) -> PRReviewActionResponse:
    """Puts a pull request review in needinfo state."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/needinfo", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def clear_needinfo_review(
    conn: Connection, req: PRReviewClearNeedInfoRequest
) -> PRReviewActionResponse:
    """Clears needinfo state on a pull request."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/clear_needinfo", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)


def reopen_review(conn: Connection, req: PRReviewReopenRequest) -> PRReviewActionResponse:
    """Reopens a declined pull request review."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr_review/reopen", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReviewActionResponse)
