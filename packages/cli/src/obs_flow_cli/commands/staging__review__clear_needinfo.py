import click


@click.command(name="clear-needinfo")
@click.argument("staging_id", type=click.INT)
@click.option("-m", "--message", required=True, help="The explanation or answer to the requested info")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, message: str, override: bool) -> None:
    """Clear needinfo, actor is the staging author."""

    import os
    from obs_flow_client import clear_needinfo_staging_review
    from obs_flow_common.messages import StagingReviewClearNeedInfoRequest
    from ..helpers import get_connection
    from ..output.review import ReviewRenderer

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = StagingReviewClearNeedInfoRequest(
        staging_id=staging_id,
        message=message,
        override=override,
    )
    with get_connection() as conn:
        res = clear_needinfo_staging_review(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=output, verbose=verbose)
