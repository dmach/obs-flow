import click

from obs_flow_cli.types import PR_ID


@click.command(name="approve")
@click.argument("pull_request_id", type=PR_ID)
@click.option("--reviewer", help="The reviewer (user or @group) to approve on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, reviewer: str | None, override: bool) -> None:
    """Approve a pull request review."""

    import os
    from obs_flow_client import approve_review
    from obs_flow_common.messages import PRReviewApproveRequest
    from ..helpers import get_connection
    from ..output.review import ReviewRenderer

    req = PRReviewApproveRequest(
        pull_request_id=pull_request_id,
        reviewer=reviewer,
        override=override,
    )
    with get_connection() as conn:
        res = approve_review(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=output, verbose=verbose)
