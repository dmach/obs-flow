import os
import sys

import click

from .lazy_group import LazyGroup


@click.group(cls=LazyGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, verbose: bool, traceback: bool) -> None:
    """
    flow: OBS Flow command-line interface
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    if verbose:
        os.environ["OBS_FLOW_VERBOSE"] = "1"


def run() -> None:
    """
    Entrypoint that runs the main CLI.
    """
    main()
