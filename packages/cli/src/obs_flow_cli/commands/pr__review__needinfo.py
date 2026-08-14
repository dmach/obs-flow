import click

from obs_flow_cli.types import PR_ID


@click.command(name="needinfo")
@click.argument("pull_request_id", type=PR_ID)
@click.option("-m", "--message", required=True, help="The information requested")
@click.option("--reviewer", help="The reviewer (user or @group) to ask for info on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, message: str, reviewer: str | None, override: bool) -> None:
    """Put a pull request review in a needinfo state."""

    import os
    from obs_flow_client import needinfo_review
    from obs_flow_common.messages import PRReviewNeedInfoRequest
    from ..helpers import get_connection
    from ..output.review import ReviewRenderer

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = PRReviewNeedInfoRequest(
        pull_request_id=pull_request_id,
        message=message,
        reviewer=reviewer,
        override=override,
    )
    with get_connection() as conn:
        res = needinfo_review(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=output, verbose=verbose)
