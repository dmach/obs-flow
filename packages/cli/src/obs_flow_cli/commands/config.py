import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="config")
def cli() -> None:
    """Manage configuration."""
