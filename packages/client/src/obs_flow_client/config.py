import os
import tomllib
from dataclasses import dataclass
from typing import Any


@dataclass
class ConnectionConfig:
    url: str | None = None
    token: str | None = None


def load_raw_config() -> dict[str, Any]:
    """Loads and parses the raw TOML configuration file.

    Returns an empty dictionary if the configuration file does not exist.
    """
    config_path = os.environ.get("OBS_FLOW_CONFIG", os.path.expanduser("~/.config/flow/flow.toml"))
    if not os.path.exists(config_path):
        return {}

    with open(config_path, "rb") as f:
        try:
            return tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse config file '{config_path}': {e}")


def load_connection_config(
    login_name: str | None = None,
    raw_config: dict[str, Any] | None = None,
) -> ConnectionConfig:
    """Loads connection configuration from file and environment variables."""
    config = ConnectionConfig()
    config_data = raw_config if raw_config is not None else load_raw_config()

    # Determine login name
    # Precedence: param > env OBS_FLOW_LOGIN > config default_login
    if not login_name:
        if "OBS_FLOW_LOGIN" in os.environ:
            login_name = os.environ["OBS_FLOW_LOGIN"]
        elif "cli" in config_data and "default_login" in config_data["cli"]:
            login_name = str(config_data["cli"]["default_login"])

    logins = config_data.get("logins", {})
    if login_name:
        if login_name in logins:
            login_data = logins[login_name]
            if "url" in login_data:
                config.url = str(login_data["url"])
            if "token" in login_data:
                config.token = str(login_data["token"])
        else:
            raise ValueError(f"Login section '{login_name}' not found in config file.")

    # Override from env
    if "OBS_FLOW_SERVER_URL" in os.environ:
        config.url = os.environ["OBS_FLOW_SERVER_URL"]
    if "OBS_FLOW_TOKEN" in os.environ:
        config.token = os.environ["OBS_FLOW_TOKEN"]

    return config
