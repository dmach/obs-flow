import click

from obs_flow_cli.types import PR_ID


@click.command(name="approve")
@click.argument("pull_request_id", type=PR_ID)
@click.option("--reviewer", help="The reviewer (user or @group) to approve on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, reviewer: str | None, override: bool) -> None:
    """Approve a pull request review."""

    from obs_flow_client import pr_review_approve
    from obs_flow_common.messages import PRReviewApproveRequest
    from ..helpers import get_connection, get_config
    from ..output.review import ReviewRenderer

    req = PRReviewApproveRequest(
        pull_request_id=pull_request_id,
        reviewer=reviewer,
        override=override,
    )
    with get_connection() as conn:
        res = pr_review_approve(conn, req)

    config = get_config()

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=config.output, verbose=config.verbose)
