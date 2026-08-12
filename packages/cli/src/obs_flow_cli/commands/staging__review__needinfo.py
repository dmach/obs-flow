import click


@click.command(name="needinfo")
@click.argument("staging_id", type=click.INT)
@click.option("--reviewer", help="The reviewer (user or @group) to ask for info on behalf of")
@click.option("-m", "--message", required=True, help="The information requested")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, reviewer: str | None, message: str, override: bool) -> None:
    """Put a staging batch review in a needinfo state."""

    from obs_flow_client import needinfo_staging_review
    from obs_flow_common.messages import StagingReviewNeedInfoRequest

    from obs_flow_cli.helpers import format_review, get_connection

    req = StagingReviewNeedInfoRequest(
        staging_id=staging_id, reviewer=reviewer, message=message, override=override
    )

    with get_connection() as conn:
        res = needinfo_staging_review(conn, req)

    click.echo(f"Staging Batch ID: {click.style(str(res.staging_id), bold=True)}")
    click.echo("=" * 40)
    format_review(res.review)
