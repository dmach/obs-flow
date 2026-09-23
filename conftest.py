import os
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def isolate_flow_config():
    """Ensure tests never access ~/.config/flow/flow.toml and have default connection URL."""
    with patch.dict(
        os.environ,
        {
            "OBS_FLOW_CONFIG": "/dev/null",
            "OBS_FLOW_SERVER_URL": "http://localhost:8000",
        },
    ):
        yield
