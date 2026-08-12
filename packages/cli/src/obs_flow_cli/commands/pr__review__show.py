import click

from obs_flow_cli.types import PR_ID


@click.command(name="show")
@click.argument("pull_request_id", type=PR_ID)
@click.option("--reviewer", help="Filter by reviewer (user or @group)")
def cli(pull_request_id: str, reviewer: str | None) -> None:
    """Show pull request review details."""

    from obs_flow_client import show_review
    from obs_flow_common.messages import PRReviewShowRequest

    from obs_flow_cli.helpers import format_review, get_connection

    req = PRReviewShowRequest(pull_request_id=pull_request_id, reviewer=reviewer)

    with get_connection() as conn:
        res = show_review(conn, req)

    click.echo(f"Pull Request: {click.style(res.pull_request_id, bold=True)}")
    click.echo("=" * 40)

    if not res.reviews:
        click.echo("No reviews found.")
        return

    for review in res.reviews:
        format_review(review)
