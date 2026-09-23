import os
from dataclasses import dataclass

import click
from obs_flow_client import (
    Connection,
    ConnectionConfig,
    load_connection_config,
    load_raw_config,
    create_connection,
)


@dataclass
class CliConfig:
    verbose: bool = False
    output: str | None = None
    traceback: bool = False
    connection: ConnectionConfig = None


def get_config() -> CliConfig:
    """Returns the configuration loaded from file, env, and context."""
    cli_config = CliConfig()

    ctx = click.get_current_context(silent=True)

    # Load raw config structure via client helper
    try:
        config_data = load_raw_config()
    except ValueError as e:
        if ctx:
            raise click.UsageError(str(e))
        else:
            raise

    # Extract CLI-specific settings
    if "cli" in config_data:
        cli_data = config_data["cli"]
        if "verbose" in cli_data:
            cli_config.verbose = bool(cli_data["verbose"])
        if "output" in cli_data:
            cli_config.output = str(cli_data["output"])
        if "traceback" in cli_data:
            cli_config.traceback = bool(cli_data["traceback"])

    # Determine login name for connection config
    login_name = None
    if "cli" in config_data and "default_login" in config_data["cli"]:
        login_name = str(config_data["cli"]["default_login"])

    if "OBS_FLOW_LOGIN" in os.environ:
        login_name = os.environ["OBS_FLOW_LOGIN"]

    if ctx:
        root_ctx = ctx.find_root()
        if root_ctx and root_ctx.params and root_ctx.params.get("login"):
            login_name = root_ctx.params["login"]

    # Load connection config using already loaded raw config
    try:
        cli_config.connection = load_connection_config(login_name=login_name, raw_config=config_data)
    except ValueError as e:
        if ctx:
            raise click.UsageError(str(e))
        else:
            raise

    # Override CLI values from env
    if os.environ.get("OBS_FLOW_VERBOSE") == "1":
        cli_config.verbose = True
    if "OBS_FLOW_OUTPUT" in os.environ:
        cli_config.output = os.environ["OBS_FLOW_OUTPUT"]
    if os.environ.get("OBS_FLOW_TRACEBACK") == "1":
        cli_config.traceback = True

    # Override CLI values from context (command-line options)
    if ctx:
        root_ctx = ctx.find_root()
        if root_ctx and root_ctx.params:
            if root_ctx.get_parameter_source("verbose") == click.core.ParameterSource.COMMANDLINE:
                cli_config.verbose = bool(root_ctx.params.get("verbose", cli_config.verbose))
            if root_ctx.get_parameter_source("output") == click.core.ParameterSource.COMMANDLINE:
                cli_config.output = root_ctx.params.get("output")
            if root_ctx.get_parameter_source("traceback") == click.core.ParameterSource.COMMANDLINE:
                cli_config.traceback = bool(root_ctx.params.get("traceback", cli_config.traceback))

    return cli_config


def get_connection() -> Connection:
    """Returns an initialized Connection to the OBS Flow server."""
    config = get_config()
    if not config.connection or not config.connection.url:
        msg = "OBS Flow server URL is not configured. Please configure a login in flow.toml or set OBS_FLOW_SERVER_URL."
        ctx = click.get_current_context(silent=True)
        if ctx:
            raise click.UsageError(msg)
        else:
            raise ValueError(msg)
    return create_connection(config=config.connection)
