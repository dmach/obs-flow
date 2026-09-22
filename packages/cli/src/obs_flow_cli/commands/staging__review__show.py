import click


@click.command(name="show")
@click.argument("staging_id", type=click.INT)
@click.option("--reviewer", help="Filter by reviewer (user or @group)")
def cli(staging_id: int, reviewer: str | None) -> None:
    """Show staging batch review details."""

    import os
    from obs_flow_client import staging_review_show
    from obs_flow_common.messages import StagingReviewShowRequest
    from ..helpers import get_connection
    from ..output.review import ReviewRenderer

    req = StagingReviewShowRequest(
        staging_id=staging_id,
        reviewer=reviewer,
    )
    with get_connection() as conn:
        res = staging_review_show(conn, req)

    if not res.reviews:
        click.echo("No reviews found.", err=True)
        return

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewRenderer(res.reviews)
    renderer.render(fmt=output, verbose=verbose)
