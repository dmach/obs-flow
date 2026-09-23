import click


@click.command(name="clear-needinfo")
@click.argument("staging_id", type=click.INT)
@click.option("-m", "--message", required=True, help="The explanation or answer to the requested info")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, message: str, override: bool) -> None:
    """Clear needinfo, actor is the staging author."""

    from obs_flow_client import staging_review_clear_needinfo
    from obs_flow_common.messages import StagingReviewClearNeedInfoRequest
    from ..helpers import get_connection, get_config
    from ..output.review import ReviewRenderer

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = StagingReviewClearNeedInfoRequest(
        staging_id=staging_id,
        message=message,
        override=override,
    )
    with get_connection() as conn:
        res = staging_review_clear_needinfo(conn, req)

    config = get_config()

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=config.output, verbose=config.verbose)
