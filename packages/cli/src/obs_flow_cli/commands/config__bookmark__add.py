import click


@click.command(name="add")
@click.argument("name")
@click.argument("url")
def cli(name: str, url: str) -> None:
    """Add a new bookmark."""

    from obs_flow_client import bookmark_add
    from obs_flow_common.messages import BookmarkAddRequest
    from ..helpers import get_connection, get_config
    from ..output.bookmark import BookmarkRenderer

    req = BookmarkAddRequest(name=name, url=url)

    with get_connection() as conn:
        res = bookmark_add(conn, req)

    config = get_config()

    renderer = BookmarkRenderer(res.bookmark)
    renderer.render(fmt=config.output, verbose=config.verbose)
