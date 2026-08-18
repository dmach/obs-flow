import click


@click.command(name="reopen")
@click.argument("staging_id", type=click.INT)
@click.option("-m", "--message", required=True, help="The reason for reopening the review")
@click.option("--reviewer", help="The reviewer (user or @group) to reopen on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, message: str, reviewer: str | None, override: bool) -> None:
    """Reopen a declined staging batch review."""

    import os
    from obs_flow_client import reopen_staging_review
    from obs_flow_common.messages import StagingReviewReopenRequest
    from ..helpers import get_connection
    from ..output.review import ReviewRenderer

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = StagingReviewReopenRequest(
        staging_id=staging_id,
        reviewer=reviewer,
        message=message,
        override=override,
    )
    with get_connection() as conn:
        res = reopen_staging_review(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=output, verbose=verbose)
