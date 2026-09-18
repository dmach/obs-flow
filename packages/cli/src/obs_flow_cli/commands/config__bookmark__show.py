import click


@click.command(name="show")
@click.argument("name")
def cli(name: str) -> None:
    """Show a bookmark's URL."""

    import sys
    from obs_flow_client import list_bookmarks
    from obs_flow_common.messages import BookmarkListRequest
    from ..helpers import get_connection

    req = BookmarkListRequest()

    with get_connection() as conn:
        res = list_bookmarks(conn, req)

    bookmark = next((b for b in res.bookmarks if b.name.lower() == name.lower()), None)
    if not bookmark:
        click.secho(f"Error: Bookmark '{name}' not found.", fg="red", err=True)
        sys.exit(1)

    print(bookmark.url)
