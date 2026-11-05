import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="package")
def cli() -> None:
    """Manage packages."""
