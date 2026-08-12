import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="staging")
def cli() -> None:
    """Manage staging batches."""
