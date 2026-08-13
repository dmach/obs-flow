import os
import sys

import click

from .lazy_group import LazyGroup


@click.group(cls=LazyGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("--traceback", is_flag=True, help="Show full traceback on error")
@click.pass_context
def main(ctx: click.Context, verbose: bool, traceback: bool) -> None:
    """
    flow: OBS Flow command-line interface
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["traceback"] = traceback
    if verbose:
        os.environ["OBS_FLOW_VERBOSE"] = "1"
    if traceback:
        os.environ["OBS_FLOW_TRACEBACK"] = "1"


def run() -> None:
    """
    Entrypoint that runs the main CLI.
    """
    from requests.exceptions import HTTPError

    try:
        main()
    except HTTPError as e:
        if "--traceback" in sys.argv or os.environ.get("OBS_FLOW_TRACEBACK") == "1":
            raise
        print(str(e), file=sys.stderr)
        sys.exit(1)
