import click


@click.command(name="list")
@click.option("--pr", required=True, help="Pull request ID (e.g. 1 or openSUSE:Factory/pkg#1).")
def cli(pr: str) -> None:
    """List comments on a pull request."""
    from obs_flow_client import comment_list
    from obs_flow_common.messages import CommentListRequest
    from ..helpers import get_connection, get_config
    from ..output.comment import CommentRenderer

    req = CommentListRequest(
        target_type="pull_request",
        target_id=pr,
    )
    with get_connection() as conn:
        res = comment_list(conn, req)

    config = get_config()
    renderer = CommentRenderer(res.comments)
    renderer.render(fmt=config.output, verbose=config.verbose)
