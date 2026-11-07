import click
from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="staging__comment")
def cli() -> None:
    """Manage comments on staging batches."""
