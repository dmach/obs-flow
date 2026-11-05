"""Client library functions for Pull Requests.

This module provides functions to interact with the OBS Flow server's
RPC-like endpoints for managing pull requests.
"""

import msgspec
from obs_flow_common.messages import (
    PRCreateRequest,
    PRCreateResponse,
    PRReadyForReviewRequest,
    PRReadyForReviewResponse,
    PRConvertToDraftRequest,
    PRConvertToDraftResponse,
    PRMergeRequest,
    PRMergeResponse,
)

from obs_flow_client.connection import Connection


def pr_create(conn: Connection, req: PRCreateRequest) -> PRCreateResponse:
    """Creates a new pull request.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The PRCreateRequest payload.

    Returns:
        A PRCreateResponse containing the created pull request details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr/create", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRCreateResponse)


def pr_ready_for_review(conn: Connection, req: PRReadyForReviewRequest) -> PRReadyForReviewResponse:
    """Marks pull requests ready for review."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr/ready-for-review", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRReadyForReviewResponse)


def pr_convert_to_draft(conn: Connection, req: PRConvertToDraftRequest) -> PRConvertToDraftResponse:
    """Converts pull requests to draft."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr/convert-to-draft", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRConvertToDraftResponse)


def pr_merge(conn: Connection, req: PRMergeRequest) -> PRMergeResponse:
    """Merges pull requests."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/pr/merge", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PRMergeResponse)
