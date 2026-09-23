import click

from obs_flow_cli.types import PR_ID


@click.command(name="show")
@click.argument("pull_request_id", type=PR_ID)
@click.option("--reviewer", help="Filter by reviewer (user or @group)")
def cli(pull_request_id: str, reviewer: str | None) -> None:
    """Show pull request review details."""

    from obs_flow_client import pr_review_show
    from obs_flow_common.messages import PRReviewShowRequest
    from ..helpers import get_connection, get_config
    from ..output.review import ReviewRenderer

    req = PRReviewShowRequest(
        pull_request_id=pull_request_id,
        reviewer=reviewer,
    )
    with get_connection() as conn:
        res = pr_review_show(conn, req)

    if not res.reviews:
        click.echo("No reviews found.", err=True)
        return

    config = get_config()

    renderer = ReviewRenderer(res.reviews)
    renderer.render(fmt=config.output, verbose=config.verbose)
