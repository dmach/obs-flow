import click

from obs_flow_cli.types import PR_ID


@click.command(name="clear-needinfo")
@click.argument("pull_request_id", type=PR_ID)
@click.option("-m", "--message", required=True, help="The explanation or answer to the requested info")
@click.option("--reviewer", help="Clear needinfo only for this reviewer (user, @group, or role:<name>)")
@click.option("--all", "all_reviews", is_flag=True, help="Clear needinfo on all reviews")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, message: str, reviewer: str | None, all_reviews: bool, override: bool) -> None:
    """Clear needinfo state on pull request reviews."""

    from obs_flow_client import pr_review_clear_needinfo
    from obs_flow_common.messages import PRReviewClearNeedInfoRequest
    from ..helpers import get_connection, get_config
    from ..output.review import ReviewRenderer

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")
    if reviewer is not None and all_reviews:
        raise click.UsageError("--reviewer and --all are mutually exclusive.")
    if reviewer is None and not all_reviews:
        raise click.UsageError("Specify either --reviewer or --all.")

    req = PRReviewClearNeedInfoRequest(
        pull_request_id=pull_request_id,
        message=message,
        reviewer=reviewer,
        override=override,
    )
    with get_connection() as conn:
        res = pr_review_clear_needinfo(conn, req)

    config = get_config()

    renderer = ReviewRenderer(res.reviews)
    renderer.render(fmt=config.output, verbose=config.verbose)
