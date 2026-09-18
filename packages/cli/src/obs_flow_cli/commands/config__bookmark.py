import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="config__bookmark")
def cli() -> None:
    """Manage bookmarks."""
