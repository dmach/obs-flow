"""OBS Flow Client Library.

Provides programmatic access to the OBS Flow API.
"""

from obs_flow_client.connection import Connection, create_connection
from obs_flow_client.reviews import (
    approve_review,
    clear_needinfo_review,
    decline_review,
    needinfo_review,
    reopen_review,
    show_review,
)
from obs_flow_client.staging import (
    add_to_staging,
    approve_staging_review,
    clear_needinfo_staging_review,
    create_staging,
    decline_staging_review,
    edit_staging,
    needinfo_staging_review,
    remove_from_staging,
    reopen_staging_review,
    show_staging,
    show_staging_review,
)

__all__ = [
    "Connection",
    "add_to_staging",
    "approve_review",
    "approve_staging_review",
    "clear_needinfo_review",
    "clear_needinfo_staging_review",
    "create_connection",
    "create_staging",
    "decline_review",
    "decline_staging_review",
    "edit_staging",
    "needinfo_review",
    "needinfo_staging_review",
    "remove_from_staging",
    "reopen_review",
    "reopen_staging_review",
    "show_review",
    "show_staging",
    "show_staging_review",
]
