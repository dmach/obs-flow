"""
Pull request helpers shared by server, client, and CLI.
"""

import re

_TEXT_ID_REGEX = re.compile(r"^([^/]+)/([^#]+)#(\d+)$")


def pull_request_build_text_id(owner: str, repo: str, number: int) -> str:
    """
    Build a PR text ID from ``owner``, ``repo``, and ``number``.
    """
    return f"{owner}/{repo}#{number}"


def pull_request_parse_text_id(text_id: str) -> tuple[str, str, int]:
    """
    Split a PR text ID into ``(owner, repo, number)``.

    Raises ``ValueError`` if the format is invalid.
    """
    match = _TEXT_ID_REGEX.match(text_id)
    if not match:
        raise ValueError(f"Invalid pull request ID format: {text_id}")
    owner, repo, number = match.groups()
    return owner, repo, int(number)
