import os
import tempfile
from unittest.mock import patch
import click
from click.testing import CliRunner
import pytest

from obs_flow_cli.helpers import get_config, get_connection


def test_get_config_no_file():
    with patch.dict(os.environ, {}, clear=True):
        # Ensure OBS_FLOW_CONFIG points to a non-existent file
        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": "/nonexistent/flow.toml"}):
            config = get_config()
            assert config.verbose is False
            assert config.output is None
            assert config.traceback is False
            assert config.connection.url is None
            assert config.connection.token is None

            with pytest.raises(ValueError, match="OBS Flow server URL is not configured"):
                get_connection()


def test_get_config_from_file():
    config_content = """
[cli]
verbose = true
output = "json"
traceback = true
default_login = "production"

[logins.production]
url = "https://flow.example.com"
token = "secret-token"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            config = get_config()
            assert config.verbose is True
            assert config.output == "json"
            assert config.traceback is True
            assert config.connection.url == "https://flow.example.com"
            assert config.connection.token == "secret-token"


def test_get_config_precedence_env_overrides_file():
    config_content = """
[cli]
verbose = false
output = "text"

[logins.production]
url = "https://flow.example.com"
token = "secret-token"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        env = {
            "OBS_FLOW_CONFIG": f.name,
            "OBS_FLOW_VERBOSE": "1",
            "OBS_FLOW_OUTPUT": "json",
            "OBS_FLOW_LOGIN": "production",
            "OBS_FLOW_SERVER_URL": "https://env.example.com",
            "OBS_FLOW_TOKEN": "obs-env-token",
        }
        with patch.dict(os.environ, env, clear=True):
            config = get_config()
            assert config.verbose is True
            assert config.output == "json"
            assert config.connection.url == "https://env.example.com"
            assert config.connection.token == "obs-env-token"


def test_get_config_missing_login_section():
    config_content = """
[cli]
default_login = "nonexistent"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            with pytest.raises(ValueError, match="Login section 'nonexistent' not found"):
                get_config()


def test_get_config_malformed_file():
    config_content = """
[cli
verbose = true
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            with pytest.raises(ValueError, match="Failed to parse config file"):
                get_config()


def test_get_config_click_option_precedence():
    config_content = """
[cli]
verbose = false
output = "text"
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=True) as f:
        f.write(config_content)
        f.flush()

        from obs_flow_cli.cli import main

        @main.command("dummy-cmd")
        def dummy_cmd():
            config = get_config()
            click.echo(f"verbose={config.verbose},output={config.output}")

        runner = CliRunner()
        # Test with options overriding config file
        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            result = runner.invoke(main, ["--verbose", "--output", "json", "dummy-cmd"])
            assert result.exit_code == 0
            assert "verbose=True,output=json" in result.output

        # Test without options (should use config file values)
        with patch.dict(os.environ, {"OBS_FLOW_CONFIG": f.name}, clear=True):
            result = runner.invoke(main, ["dummy-cmd"])
            assert result.exit_code == 0
            assert "verbose=False,output=text" in result.output
