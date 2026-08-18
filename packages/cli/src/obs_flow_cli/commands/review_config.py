import click

from obs_flow_cli.lazy_group import LazyGroup


@click.group(cls=LazyGroup, cmd_prefix="review_config")
def cli() -> None:
    """Manage pull request review configurations."""
