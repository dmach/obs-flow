import click


@click.command(name="add")
@click.argument("name")
@click.argument("url")
def cli(name: str, url: str) -> None:
    """Add a new bookmark."""

    import os
    from obs_flow_client import add_bookmark
    from obs_flow_common.messages import BookmarkAddRequest
    from ..helpers import get_connection
    from ..output.bookmark import BookmarkRenderer

    req = BookmarkAddRequest(name=name, url=url)

    with get_connection() as conn:
        res = add_bookmark(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = BookmarkRenderer(res.bookmark)
    renderer.render(fmt=output, verbose=verbose)
