import click


@click.command(name="decline")
@click.argument("staging_id", type=click.INT)
@click.option("--reviewer", help="The reviewer (user or @group) to decline on behalf of")
@click.option("-m", "--message", required=True, help="The reason for declining the review")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, reviewer: str | None, message: str, override: bool) -> None:
    """Decline a staging batch review."""

    from obs_flow_client import decline_staging_review
    from obs_flow_common.messages import StagingReviewDeclineRequest

    from obs_flow_cli.helpers import format_review, get_connection

    req = StagingReviewDeclineRequest(
        staging_id=staging_id, reviewer=reviewer, message=message, override=override
    )

    with get_connection() as conn:
        res = decline_staging_review(conn, req)

    click.echo(f"Staging Batch ID: {click.style(str(res.staging_id), bold=True)}")
    click.echo("=" * 40)
    format_review(res.review)
