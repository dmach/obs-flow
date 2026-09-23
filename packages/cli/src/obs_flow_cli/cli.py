import os
import sys

import click

from .lazy_group import LazyGroup


@click.group(cls=LazyGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("--output", type=click.Choice(["text", "json"], case_sensitive=False), help="Output format.")
@click.option("--traceback", is_flag=True, help="Show full traceback on error")
@click.option("--login", help="The login configuration to use.")
@click.pass_context
def main(ctx: click.Context, verbose: bool, output: str, traceback: bool, login: str | None) -> None:
    """
    flow: OBS Flow command-line interface
    """
    ctx.ensure_object(dict)
    ctx.obj["output"] = output
    ctx.obj["verbose"] = verbose
    ctx.obj["traceback"] = traceback
    ctx.obj["login"] = login


def run() -> None:
    """
    Entrypoint that runs the main CLI.
    """
    from requests.exceptions import HTTPError
    from .helpers import get_config

    try:
        main()
    except HTTPError as e:
        try:
            show_traceback = get_config().traceback
        except Exception:
            show_traceback = "--traceback" in sys.argv or os.environ.get("OBS_FLOW_TRACEBACK") == "1"

        if show_traceback:
            raise
        print(str(e), file=sys.stderr)
        if e.response is not None:
            print(str(e.response.text), file=sys.stderr)
        sys.exit(1)
