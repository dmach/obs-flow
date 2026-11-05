import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="org")
def cli() -> None:
    """Manage organizations."""
