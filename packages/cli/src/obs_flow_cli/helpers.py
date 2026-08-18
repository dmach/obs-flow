import os

from obs_flow_client import Connection


def get_connection() -> Connection:
    """Returns an initialized Connection to the OBS Flow server."""
    server_url = os.environ.get("OBS_FLOW_SERVER_URL", "http://localhost:8000")
    return Connection(base_url=server_url)
