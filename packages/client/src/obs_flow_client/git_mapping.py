"""Client library functions for Git Mappings.

This module provides functions to interact with the OBS Flow server's
endpoints for managing git mappings.
"""

import msgspec
from obs_flow_common.messages import (
    GitMappingListRequest,
    GitMappingListResponse,
    GitMappingAddRequest,
    GitMappingAddResponse,
    GitMappingRemoveRequest,
    GitMappingRemoveResponse,
    GitMappingEditRequest,
    GitMappingEditResponse,
)

from obs_flow_client.connection import Connection


def list_git_mappings(conn: Connection, req: GitMappingListRequest) -> GitMappingListResponse:
    """Retrieves a list of all git mappings.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The GitMappingListRequest payload.

    Returns:
        A GitMappingListResponse containing the list of git mappings.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/git-mapping/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=GitMappingListResponse)


def add_git_mapping(conn: Connection, req: GitMappingAddRequest) -> GitMappingAddResponse:
    """Adds a new git mapping.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The GitMappingAddRequest payload.

    Returns:
        A GitMappingAddResponse containing the created git mapping.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/git-mapping/add", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=GitMappingAddResponse)


def remove_git_mapping(conn: Connection, req: GitMappingRemoveRequest) -> GitMappingRemoveResponse:
    """Removes an existing git mapping.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The GitMappingRemoveRequest payload.

    Returns:
        A GitMappingRemoveResponse indicating success.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/git-mapping/remove", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=GitMappingRemoveResponse)


def edit_git_mapping(conn: Connection, req: GitMappingEditRequest) -> GitMappingEditResponse:
    """Edits an existing git mapping.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The GitMappingEditRequest payload.

    Returns:
        A GitMappingEditResponse containing the updated git mapping.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/git-mapping/edit", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=GitMappingEditResponse)
