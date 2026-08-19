"""OBS Flow Client Library.

Provides programmatic access to the OBS Flow API.
"""

from obs_flow_client.connection import Connection, create_connection
from obs_flow_client.git_mapping import (
    list_git_mappings,
    add_git_mapping,
    remove_git_mapping,
    edit_git_mapping,
)
from obs_flow_client.reviews import (
    add_review_config,
    approve_review,
    clear_needinfo_review,
    decline_review,
    list_review_configs,
    needinfo_review,
    remove_review_config,
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
    "add_git_mapping",
    "add_review_config",
    "add_to_staging",
    "approve_review",
    "approve_staging_review",
    "clear_needinfo_review",
    "clear_needinfo_staging_review",
    "create_connection",
    "create_staging",
    "decline_review",
    "decline_staging_review",
    "edit_git_mapping",
    "edit_staging",
    "list_git_mappings",
    "list_review_configs",
    "needinfo_review",
    "needinfo_staging_review",
    "remove_from_staging",
    "remove_git_mapping",
    "remove_review_config",
    "reopen_review",
    "reopen_staging_review",
    "show_review",
    "show_staging",
    "show_staging_review",
]
