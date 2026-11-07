import click


@click.command(name="list")
@click.option("--batch", required=True, help="Staging batch ID.")
def cli(batch: str) -> None:
    """List comments on a staging batch."""
    from obs_flow_client import comment_list
    from obs_flow_common.messages import CommentListRequest
    from ..helpers import get_connection, get_config
    from ..output.comment import CommentRenderer

    req = CommentListRequest(
        target_type="staging_batch",
        target_id=batch,
    )
    with get_connection() as conn:
        res = comment_list(conn, req)

    config = get_config()
    renderer = CommentRenderer(res.comments)
    renderer.render(fmt=config.output, verbose=config.verbose)
