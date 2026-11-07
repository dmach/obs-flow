import click


@click.command(name="add")
@click.option("--batch", required=True, help="Staging batch ID.")
@click.option("--author", required=True, help="Author username.")
@click.option("--body", required=True, help="Comment body.")
def cli(batch: str, author: str, body: str) -> None:
    """Add a comment to a staging batch."""
    from obs_flow_client import comment_add
    from obs_flow_common.messages import CommentAddRequest
    from ..helpers import get_connection, get_config
    from ..output.comment import CommentRenderer

    req = CommentAddRequest(
        target_type="staging_batch",
        target_id=batch,
        author=author,
        body=body,
    )
    with get_connection() as conn:
        res = comment_add(conn, req)

    config = get_config()
    renderer = CommentRenderer(res.comment)
    renderer.render(fmt=config.output, verbose=config.verbose)
