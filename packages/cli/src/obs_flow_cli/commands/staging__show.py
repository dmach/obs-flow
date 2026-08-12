import click


@click.command(name="show")
@click.argument("staging_id", type=click.INT)
def cli(staging_id: int) -> None:
    """Show pull staging details."""

    from obs_flow_client import show_staging

    from obs_flow_cli.helpers import get_connection

    with get_connection() as conn:
        res = show_staging(conn, staging_id)

    click.echo(f"Staging Batch ID: {click.style(str(res.id), bold=True)}")
    click.echo("=" * 40)
    click.echo(f"Title:          {res.title or 'N/A'}")
    click.echo(f"Creator:        {res.creator or 'N/A'}")
    click.echo(f"State:          {click.style(res.state.upper(), fg='green' if res.state == 'collecting' else 'yellow', bold=True)}")
    click.echo(f"Target Project: {res.target_project or 'N/A'}")
    if res.embargo_date:
        click.echo(f"Embargo Date:   {res.embargo_date}")
    if res.release_date:
        click.echo(f"Release Date:   {res.release_date}")
    click.echo("-" * 40)
    click.echo("Included Pull Requests:")
    if not res.pull_requests:
        click.echo("  No pull requests included.")
    else:
        for pr in res.pull_requests:
            click.echo(f"  - {pr}")
