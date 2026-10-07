"""Client library functions for Projects.

This module provides functions to interact with the OBS Flow server's
RPC-like endpoints for managing projects.
"""

import msgspec
from obs_flow_common.messages import (
    ProjectListRequest,
    ProjectListResponse,
    ProjectUpdateRequest,
    ProjectUpdateResponse,
)

from obs_flow_client.connection import Connection


def project_list(conn: Connection, req: ProjectListRequest) -> ProjectListResponse:
    """Lists all projects.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The ProjectListRequest payload.

    Returns:
        A ProjectListResponse containing the list of projects.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/project/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ProjectListResponse)


def project_update(conn: Connection, req: ProjectUpdateRequest) -> ProjectUpdateResponse:
    """Updates an existing project.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The ProjectUpdateRequest payload.

    Returns:
        A ProjectUpdateResponse containing the updated project details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/project/update", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=ProjectUpdateResponse)

