"""Client library functions for Packages.

This module provides functions to interact with the OBS Flow server's
RPC-like endpoints for managing packages.
"""

import msgspec
from obs_flow_common.messages import (
    PackageListRequest,
    PackageListResponse,
    PackageShowRequest,
    PackageShowResponse,
    PackageCreateRequest,
    PackageCreateResponse,
)

from obs_flow_client.connection import Connection


def package_list(conn: Connection, req: PackageListRequest) -> PackageListResponse:
    """Lists packages.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The PackageListRequest payload.

    Returns:
        A PackageListResponse containing the list of packages.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/package/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PackageListResponse)


def package_show(conn: Connection, req: PackageShowRequest) -> PackageShowResponse:
    """Shows an existing package.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The PackageShowRequest payload.

    Returns:
        A PackageShowResponse containing the package details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/package/show", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PackageShowResponse)


def package_create(conn: Connection, req: PackageCreateRequest) -> PackageCreateResponse:
    """Creates a new package.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The PackageCreateRequest payload.

    Returns:
        A PackageCreateResponse containing the created package details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/package/create", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=PackageCreateResponse)
