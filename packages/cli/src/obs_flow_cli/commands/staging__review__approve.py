import click


@click.command(name="approve")
@click.argument("staging_id", type=click.INT)
@click.option("--reviewer", help="The reviewer (user or @group) to approve on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, reviewer: str | None, override: bool) -> None:
    """Approve a staging batch review."""

    from obs_flow_client import staging_review_approve
    from obs_flow_common.messages import StagingReviewApproveRequest
    from ..helpers import get_connection, get_config
    from ..output.review import ReviewRenderer

    req = StagingReviewApproveRequest(
        staging_id=staging_id,
        reviewer=reviewer,
        override=override,
    )
    with get_connection() as conn:
        res = staging_review_approve(conn, req)

    config = get_config()

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=config.output, verbose=config.verbose)
