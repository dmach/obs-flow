import click


@click.command(name="list")
@click.option("--name", "names", multiple=True, help="Filter by exact bookmark name(s). Can be specified multiple times.")
@click.option("--name-contains", "name_contains", multiple=True, help="Filter by partial bookmark name(s). Can be specified multiple times.")
def cli(names: tuple[str, ...], name_contains: tuple[str, ...]) -> None:
    """List bookmarks."""

    from obs_flow_client import bookmark_list
    from obs_flow_common.messages import BookmarkListRequest
    from ..helpers import get_connection, get_config
    from ..output.bookmark import BookmarkRenderer

    req = BookmarkListRequest(
        names=list(names) if names else None,
        name_contains=list(name_contains) if name_contains else None,
    )

    with get_connection() as conn:
        res = bookmark_list(conn, req)

    if not res.bookmarks:
        click.echo("No bookmarks found.", err=True)
        return

    config = get_config()

    renderer = BookmarkRenderer(res.bookmarks)
    renderer.render(fmt=config.output, verbose=config.verbose)
