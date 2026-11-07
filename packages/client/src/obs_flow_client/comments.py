"""Client library functions for Comments.

Provides functions to interact with the OBS Flow server's RPC endpoints
for adding and listing comments on Pull Requests and Staging Batches.
"""

import msgspec
from obs_flow_common.messages import (
    CommentAddRequest,
    CommentAddResponse,
    CommentListRequest,
    CommentListResponse,
)

from obs_flow_client.connection import Connection


def comment_add(conn: Connection, req: CommentAddRequest) -> CommentAddResponse:
    """Adds a new comment to a pull request or staging batch."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/comment/add", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=CommentAddResponse)


def comment_list(conn: Connection, req: CommentListRequest) -> CommentListResponse:
    """Lists comments for a pull request or staging batch."""
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/comment/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=CommentListResponse)
