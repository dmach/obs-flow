"""Client library functions for Orgs.

This module provides functions to interact with the OBS Flow server's
RPC-like endpoints for managing organizations.
"""

import msgspec
from obs_flow_common.messages import (
    OrgListRequest,
    OrgListResponse,
    OrgCreateRequest,
    OrgCreateResponse,
)

from obs_flow_client.connection import Connection


def org_list(conn: Connection, req: OrgListRequest) -> OrgListResponse:
    """Lists all organizations.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The OrgListRequest payload.

    Returns:
        An OrgListResponse containing the list of orgs.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/org/list", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=OrgListResponse)


def org_create(conn: Connection, req: OrgCreateRequest) -> OrgCreateResponse:
    """Creates a new organization.

    Args:
        conn: The Connection instance to the OBS Flow server.
        req: The OrgCreateRequest payload.

    Returns:
        An OrgCreateResponse containing the created org details.
    """
    serialized_data = msgspec.json.encode(req)
    response_bytes = conn.post("/api/v1/org/create", data=serialized_data)
    return msgspec.json.decode(response_bytes, type=OrgCreateResponse)
