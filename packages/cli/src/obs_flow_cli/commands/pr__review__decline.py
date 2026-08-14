import click

from obs_flow_cli.types import PR_ID


@click.command(name="decline")
@click.argument("pull_request_id", type=PR_ID)
@click.option("-m", "--message", required=True, help="The reason for declining the review")
@click.option("--reviewer", help="The reviewer (user or @group) to decline on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, message: str, reviewer: str | None, override: bool) -> None:
    """Decline a pull request review."""

    import os
    from obs_flow_client import decline_review
    from obs_flow_common.messages import PRReviewDeclineRequest
    from ..helpers import get_connection
    from ..output.review import ReviewRenderer

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = PRReviewDeclineRequest(
        pull_request_id=pull_request_id,
        message=message,
        reviewer=reviewer,
        override=override,
    )
    with get_connection() as conn:
        res = decline_review(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=output, verbose=verbose)
