"""Client library functions for Bookmarks.

This module provides functions to interact with the OBS Flow server's
endpoints for managing bookmarks.
"""

import msgspec
from obs_flow_common.messages import (
    BookmarkListRequest,
    BookmarkListResponse,
    BookmarkAddRequest,
    BookmarkAddResponse,
    BookmarkRemoveRequest,
    BookmarkRemoveResponse,
    BookmarkImportRequest,
    BookmarkImportResponse,
)

from obs_flow_client.connection import Connection


def bookmark_list(conn: Connection, req: BookmarkListRequest) -> BookmarkListResponse:
    """Retrieves a list of bookmarks.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The BookmarkListRequest payload.

    Returns:
        A BookmarkListResponse containing the list of bookmarks.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/bookmark/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=BookmarkListResponse)


def bookmark_add(conn: Connection, req: BookmarkAddRequest) -> BookmarkAddResponse:
    """Adds a new bookmark.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The BookmarkAddRequest payload.

    Returns:
        A BookmarkAddResponse containing the created bookmark.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/bookmark/add", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=BookmarkAddResponse)


def bookmark_remove(conn: Connection, req: BookmarkRemoveRequest) -> BookmarkRemoveResponse:
    """Removes an existing bookmark.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The BookmarkRemoveRequest payload.

    Returns:
        A BookmarkRemoveResponse indicating success.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/bookmark/remove", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=BookmarkRemoveResponse)


def bookmark_import(conn: Connection, req: BookmarkImportRequest) -> BookmarkImportResponse:
    """Imports bookmarks from a list.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The BookmarkImportRequest payload.

    Returns:
        A BookmarkImportResponse containing the counts of imported and updated bookmarks.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/bookmark/import", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=BookmarkImportResponse)
