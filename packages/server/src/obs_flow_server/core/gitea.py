"""
Shared helpers for Gitea.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings


def merge_pull_request(owner: str, repo: str, number: int) -> None:
    if not getattr(settings, "GITEA_URL", None) or not getattr(settings, "GITEA_TOKEN", None):
        raise ValueError("GITEA_URL and GITEA_TOKEN must be configured.")

    url = f"{settings.GITEA_URL.rstrip('/')}/api/v1/repos/{owner}/{repo}/pulls/{number}/merge"
    headers = {
        "Authorization": f"token {settings.GITEA_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = json.dumps({"Do": "merge"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status not in (200, 204):
                raise ValueError(f"Failed to merge PR #{number} in Gitea: status {response.status}")
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise ValueError(f"Failed to merge PR #{number} in Gitea: {error_msg}")
    except Exception as e:
        raise ValueError(f"Failed to merge PR #{number} in Gitea: {e}")
