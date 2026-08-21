import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="config__git_mapping")
def cli() -> None:
    """Manage git mappings."""
