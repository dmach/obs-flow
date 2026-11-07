import click
from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="pr__comment")
def cli() -> None:
    """Manage comments on pull requests."""
