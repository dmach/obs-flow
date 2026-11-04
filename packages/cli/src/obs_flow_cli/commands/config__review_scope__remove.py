import click


@click.command(name="remove")
@click.option("--name", required=True, help="The name of the scope to remove.")
def cli(name: str) -> None:
    """Remove a review scope."""

    from obs_flow_client import review_scope_remove
    from obs_flow_common.messages import ReviewScopeRemoveRequest
    from ..helpers import get_connection

    req = ReviewScopeRemoveRequest(name=name)
    with get_connection() as conn:
        res = review_scope_remove(conn, req)

    if res.success:
        click.echo(f"Successfully removed review scope '{name}'.")
    else:
        click.echo(f"Review scope '{name}' not found.", err=True)
        raise click.ClickException(f"Review scope '{name}' not found.")
