import click


@click.command(name="edit")
@click.argument("staging_id", type=click.INT)
@click.option("--title", help="Update the descriptive title for the staging batch")
@click.option("--embargo-date", help="Update the planned embargo date (ISO-8601 format)")
@click.option("--release-date", help="Update the planned release date (ISO-8601 format)")
def cli(staging_id: int, title: str | None, embargo_date: str | None, release_date: str | None) -> None:
    """Edit an existing staging batch."""

    from obs_flow_client import edit_staging
    from obs_flow_common.messages import StagingEditRequest

    from obs_flow_cli.helpers import get_connection

    req = StagingEditRequest(id=staging_id, title=title, embargo_date=embargo_date, release_date=release_date)

    with get_connection() as conn:
        res = edit_staging(conn, req)

    click.echo(f"Staging batch {click.style(str(res.id), bold=True)} updated successfully.")
    if res.title:
        click.echo(f"Title: {res.title}")
    if res.embargo_date:
        click.echo(f"Embargo Date: {res.embargo_date}")
    if res.release_date:
        click.echo(f"Release Date: {res.release_date}")
