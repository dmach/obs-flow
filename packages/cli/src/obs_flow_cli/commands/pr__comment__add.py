import click


@click.command(name="add")
@click.option("--pr", required=True, help="Pull request ID (e.g. 1 or openSUSE:Factory/pkg#1).")
@click.option("--author", required=True, help="Author username.")
@click.option("--body", required=True, help="Comment body.")
def cli(pr: str, author: str, body: str) -> None:
    """Add a comment to a pull request."""
    from obs_flow_client import comment_add
    from obs_flow_common.messages import CommentAddRequest
    from ..helpers import get_connection, get_config
    from ..output.comment import CommentRenderer

    req = CommentAddRequest(
        target_type="pull_request",
        target_id=pr,
        author=author,
        body=body,
    )
    with get_connection() as conn:
        res = comment_add(conn, req)

    config = get_config()
    renderer = CommentRenderer(res.comment)
    renderer.render(fmt=config.output, verbose=config.verbose)
