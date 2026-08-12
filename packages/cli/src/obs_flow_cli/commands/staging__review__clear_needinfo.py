import click


@click.command(name="clear-needinfo")
@click.argument("staging_id", type=click.INT)
@click.option("-m", "--message", required=True, help="The explanation or answer to the requested info")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(staging_id: int, message: str, override: bool) -> None:
    """Clear needinfo, actor is the staging author."""

    from obs_flow_client import clear_needinfo_staging_review
    from obs_flow_common.messages import StagingReviewClearNeedInfoRequest

    from obs_flow_cli.helpers import format_review, get_connection

    req = StagingReviewClearNeedInfoRequest(
        staging_id=staging_id, message=message, override=override
    )

    with get_connection() as conn:
        res = clear_needinfo_staging_review(conn, req)

    click.echo(f"Staging Batch ID: {click.style(str(res.staging_id), bold=True)}")
    click.echo("=" * 40)
    format_review(res.review)
