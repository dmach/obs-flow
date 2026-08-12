import click


@click.command(name="create")
@click.option("--title", help="A descriptive title for the staging batch")
@click.option("--just-print-id", is_flag=True, help="Only print the created staging ID (useful for scripting)")
@click.option("--embargo-date", help="Planned embargo date (ISO-8601 format)")
@click.option("--release-date", help="Planned release date (ISO-8601 format)")
def cli(title: str | None, just_print_id: bool, embargo_date: str | None, release_date: str | None) -> None:
    """Create a new staging batch."""

    from obs_flow_client import create_staging
    from obs_flow_common.messages import StagingCreateRequest

    from obs_flow_cli.helpers import get_connection

    req = StagingCreateRequest(title=title, embargo_date=embargo_date, release_date=release_date)

    with get_connection() as conn:
        res = create_staging(conn, req)

    if just_print_id:
        click.echo(res.id)
    else:
        click.echo(f"Staging batch {click.style(str(res.id), bold=True)} created successfully.")
        if res.title:
            click.echo(f"Title: {res.title}")
        if res.embargo_date:
            click.echo(f"Embargo Date: {res.embargo_date}")
        if res.release_date:
            click.echo(f"Release Date: {res.release_date}")
