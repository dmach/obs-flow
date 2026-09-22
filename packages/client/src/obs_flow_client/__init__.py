"""OBS Flow Client Library.

Provides programmatic access to the OBS Flow API.
"""

from obs_flow_client.connection import Connection, create_connection
from obs_flow_client.bookmarks import (
    bookmark_add,
    bookmark_import,
    bookmark_list,
    bookmark_remove,
)
from obs_flow_client.git_mapping import (
    git_mapping_add,
    git_mapping_edit,
    git_mapping_list,
    git_mapping_remove,
)
from obs_flow_client.reviews import (
    pr_review_approve,
    pr_review_clear_needinfo,
    pr_review_decline,
    pr_review_needinfo,
    pr_review_reopen,
    pr_review_show,
    review_config_add,
    review_config_list,
    review_config_remove,
)
from obs_flow_client.staging import (
    staging_add,
    staging_create,
    staging_edit,
    staging_remove,
    staging_review_approve,
    staging_review_clear_needinfo,
    staging_review_decline,
    staging_review_needinfo,
    staging_review_reopen,
    staging_review_show,
    staging_show,
)

__all__ = [
    "Connection",
    "bookmark_add",
    "bookmark_import",
    "bookmark_list",
    "bookmark_remove",
    "create_connection",
    "git_mapping_add",
    "git_mapping_edit",
    "git_mapping_list",
    "git_mapping_remove",
    "pr_review_approve",
    "pr_review_clear_needinfo",
    "pr_review_decline",
    "pr_review_needinfo",
    "pr_review_reopen",
    "pr_review_show",
    "review_config_add",
    "review_config_list",
    "review_config_remove",
    "staging_add",
    "staging_create",
    "staging_edit",
    "staging_remove",
    "staging_review_approve",
    "staging_review_clear_needinfo",
    "staging_review_decline",
    "staging_review_needinfo",
    "staging_review_reopen",
    "staging_review_show",
    "staging_show",
]
