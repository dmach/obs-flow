import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="pr")
def cli() -> None:
    """Manage pull requests."""
