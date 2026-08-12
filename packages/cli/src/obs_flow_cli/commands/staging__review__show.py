import click


@click.command(name="show")
@click.argument("staging_id", type=click.INT)
@click.option("--reviewer", help="Filter by reviewer (user or @group)")
def cli(staging_id: int, reviewer: str | None) -> None:
    """Show staging batch review details."""

    from obs_flow_client import show_staging_review
    from obs_flow_common.messages import StagingReviewShowRequest

    from obs_flow_cli.helpers import format_review, get_connection

    req = StagingReviewShowRequest(staging_id=staging_id, reviewer=reviewer)

    with get_connection() as conn:
        res = show_staging_review(conn, req)

    click.echo(f"Staging Batch ID: {click.style(str(res.staging_id), bold=True)}")
    click.echo("=" * 40)

    if not res.reviews:
        click.echo("No reviews found.")
        return

    for review in res.reviews:
        format_review(review)
