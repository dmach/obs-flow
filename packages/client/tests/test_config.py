import os
import tempfile
from unittest.mock import patch
import pytest

from obs_flow_client import load_connection_config, create_connection, load_raw_config


def test_load_raw_config():
    config_content = """
[cli]
verbose = true
default_login = "test"

[logins.test]
url = "http://example.com"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            raw = load_raw_config()
            assert raw["cli"]["verbose"] is True
            assert raw["cli"]["default_login"] == "test"
            assert raw["logins"]["test"]["url"] == "http://example.com"

        # Non-existent file should return empty dict
        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": "/nonexistent/flow.toml"}, clear=True):
            assert load_raw_config() == {}


def test_load_connection_config_no_file():
    with patch.dict(os.environ, {}, clear=True):
        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": "/nonexistent/flow.toml"}):
            config = load_connection_config()
            assert config.url is None
            assert config.token is None

            with pytest.raises(ValueError, match="OBS Flow server URL is not configured"):
                create_connection(config=config)


def test_load_connection_config_from_file():
    config_content = """
[cli]
default_login = "production"

[logins.production]
url = "https://flow.example.com"
token = "secret-token"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            config = load_connection_config()
            assert config.url == "https://flow.example.com"
            assert config.token == "secret-token"


def test_load_connection_config_precedence_env_overrides_file():
    config_content = """
[logins.production]
url = "https://flow.example.com"
token = "secret-token"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        env = {
            "OBS_FLOW_CONFIG": f.name,
            "OBS_FLOW_LOGIN": "production",
            "OBS_FLOW_SERVER_URL": "https://env.example.com",
            "OBS_FLOW_TOKEN": "obs-env-token",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_connection_config()
            assert config.url == "https://env.example.com"
            assert config.token == "obs-env-token"


def test_load_connection_config_missing_login_section():
    config_content = """
[cli]
default_login = "nonexistent"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            with pytest.raises(ValueError, match="Login section 'nonexistent' not found"):
                load_connection_config()


def test_load_connection_config_malformed_file():
    config_content = """
[cli
verbose = true
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            with pytest.raises(ValueError, match="Failed to parse config file"):
                load_connection_config()
