import click


@click.command(name="remove")
@click.argument("name")
def cli(name: str) -> None:
    """Remove a bookmark."""

    from obs_flow_client import bookmark_remove
    from obs_flow_common.messages import BookmarkRemoveRequest
    from ..helpers import get_connection

    req = BookmarkRemoveRequest(name=name)

    with get_connection() as conn:
        res = bookmark_remove(conn, req)

    if res.success:
        click.echo(f"Successfully removed bookmark '{name}'.")
    else:
        click.echo(f"Failed to remove bookmark '{name}' (not found).", err=True)
        raise click.ClickException(f"Bookmark '{name}' not found.")
