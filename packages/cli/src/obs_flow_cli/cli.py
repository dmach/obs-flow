import os
import sys
from typing import Any

import click

from .lazy_group import LazyGroup


def extract_global_options(args: list[str]) -> tuple[list[str], dict[str, Any]]:
    """
    Extracts global options (like --verbose) from anywhere in the command line arguments.

    This allows global options to be placed anywhere in the command string.
    """
    cleaned_args: list[str] = []
    global_opts: dict[str, Any] = {"verbose": False}

    for arg in args:
        if arg in ("-v", "--verbose"):
            global_opts["verbose"] = True
        else:
            cleaned_args.append(arg)

    return cleaned_args, global_opts


@click.group(cls=LazyGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    flow: OBS Flow command-line interface
    """
    # Context initialization can be done here if needed


def run() -> None:
    """
    Entrypoint that extracts global options and runs the main CLI.
    """
    args, global_opts = extract_global_options(sys.argv[1:])

    # Store global options in environment or a shared state if needed
    if global_opts["verbose"]:
        os.environ["OBS_FLOW_VERBOSE"] = "1"

    main(args=args)
