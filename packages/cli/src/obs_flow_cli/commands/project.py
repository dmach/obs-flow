import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="project")
def cli() -> None:
    """Manage projects."""
