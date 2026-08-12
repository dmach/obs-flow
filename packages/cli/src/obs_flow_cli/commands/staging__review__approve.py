import click


@click.command(name="approve")
@click.argument("staging_id", type=click.INT)
@click.option("--reviewer", help="The reviewer (user or @group) to approve on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, reviewer: str | None, override: bool) -> None:
    """Approve a staging batch review."""

    from obs_flow_client import approve_staging_review
    from obs_flow_common.messages import StagingReviewApproveRequest

    from obs_flow_cli.helpers import format_review, get_connection

    req = StagingReviewApproveRequest(staging_id=staging_id, reviewer=reviewer, override=override)

    with get_connection() as conn:
        res = approve_staging_review(conn, req)

    click.echo(f"Staging Batch ID: {click.style(str(res.staging_id), bold=True)}")
    click.echo("=" * 40)
    format_review(res.review)
