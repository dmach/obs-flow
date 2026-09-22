"""Client library functions for Staging Batches and Staging Reviews.

This module provides functions to interact with the OBS Flow server's
RPC-like endpoints for managing staging batches and their reviews.
"""

import msgspec
from obs_flow_common.messages import (
    StagingAddRequest,
    StagingAddResponse,
    StagingCreateRequest,
    StagingCreateResponse,
    StagingDetail,
    StagingEditRequest,
    StagingEditResponse,
    StagingRemoveRequest,
    StagingRemoveResponse,
    StagingReviewActionResponse,
    StagingReviewApproveRequest,
    StagingReviewClearNeedInfoRequest,
    StagingReviewDeclineRequest,
    StagingReviewNeedInfoRequest,
    StagingReviewReopenRequest,
    StagingReviewShowRequest,
    StagingReviewShowResponse,
)

from obs_flow_client.connection import Connection


def staging_show(conn: Connection, staging_id: int) -> StagingDetail:
    """Retrieves details for a staging batch.

    Args:
        conn: The Connection instance to the OBS Flow server.
        staging_id: The unique ID of the staging batch.

    Returns:
        A StagingDetail object containing the staging batch details.
    """
    response_bytes = conn.post(f"/api/v1/staging/show/{staging_id}", data=b"")
    return msgspec.json.decode(response_bytes, type=StagingDetail)


def staging_create(conn: Connection, req: StagingCreateRequest) -> StagingCreateResponse:
    """Creates a new staging batch.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingCreateRequest payload.

    Returns:
        A StagingCreateResponse containing the created staging batch details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging/create", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingCreateResponse)


def staging_edit(conn: Connection, req: StagingEditRequest) -> StagingEditResponse:
    """Edits an existing staging batch.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingEditRequest payload.

    Returns:
        A StagingEditResponse containing the updated staging batch details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging/edit", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingEditResponse)


def staging_add(conn: Connection, req: StagingAddRequest) -> StagingAddResponse:
    """Adds pull requests to a staging batch.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingAddRequest payload.

    Returns:
        A StagingAddResponse containing the updated list of pull requests.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging/add", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingAddResponse)


def staging_remove(conn: Connection, req: StagingRemoveRequest) -> StagingRemoveResponse:
    """Removes pull requests from a staging batch.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingRemoveRequest payload.

    Returns:
        A StagingRemoveResponse containing the updated list of pull requests.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging/remove", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingRemoveResponse)


# =====================================================================
# Staging Review Functions
# =====================================================================

def staging_review_show(
    conn: Connection, req: StagingReviewShowRequest
) -> StagingReviewShowResponse:
    """Retrieves review details for a staging batch.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingReviewShowRequest payload.

    Returns:
        A StagingReviewShowResponse containing the review details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging_review/show", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingReviewShowResponse)


def staging_review_approve(
    conn: Connection, req: StagingReviewApproveRequest
) -> StagingReviewActionResponse:
    """Approves a staging batch review.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingReviewApproveRequest payload.

    Returns:
        A StagingReviewActionResponse containing the updated review state.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging_review/approve", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingReviewActionResponse)


def staging_review_decline(
    conn: Connection, req: StagingReviewDeclineRequest
) -> StagingReviewActionResponse:
    """Declines a staging batch review.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingReviewDeclineRequest payload.

    Returns:
        A StagingReviewActionResponse containing the updated review state.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging_review/decline", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingReviewActionResponse)


def staging_review_needinfo(
    conn: Connection, req: StagingReviewNeedInfoRequest
) -> StagingReviewActionResponse:
    """Puts a staging batch review in needinfo state.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingReviewNeedInfoRequest payload.

    Returns:
        A StagingReviewActionResponse containing the updated review state.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging_review/needinfo", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingReviewActionResponse)


def staging_review_clear_needinfo(
    conn: Connection, req: StagingReviewClearNeedInfoRequest
) -> StagingReviewActionResponse:
    """Clears needinfo state on a staging batch review.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingReviewClearNeedInfoRequest payload.

    Returns:
        A StagingReviewActionResponse containing the updated review state.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging_review/clear_needinfo", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingReviewActionResponse)


def staging_review_reopen(
    conn: Connection, req: StagingReviewReopenRequest
) -> StagingReviewActionResponse:
    """Reopens a declined staging batch review.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The StagingReviewReopenRequest payload.

    Returns:
        A StagingReviewActionResponse containing the updated review state.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/staging_review/reopen", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=StagingReviewActionResponse)
