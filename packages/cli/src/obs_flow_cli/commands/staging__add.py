import click

from obs_flow_cli.types import PR_ID


@click.command(name="add")
@click.argument("staging_id", type=click.INT)
@click.argument("pull_request_ids", type=PR_ID, nargs=-1, required=True)
@click.option("--allow-duplicates", is_flag=True, help="Allow adding a PR into staging even if it belongs to another staging already")
def cli(staging_id: int, pull_request_ids: tuple[str, ...], allow_duplicates: bool) -> None:
    """Add pull requests to a staging batch."""

    from obs_flow_client import add_to_staging
    from obs_flow_common.messages import StagingAddRequest

    from obs_flow_cli.helpers import get_connection

    req = StagingAddRequest(
        id=staging_id,
        pull_request_ids=list(pull_request_ids),
        allow_duplicates=allow_duplicates,
    )

    with get_connection() as conn:
        res = add_to_staging(conn, req)

    click.echo(f"Successfully added pull requests to staging batch {click.style(str(res.id), bold=True)}.")
    click.echo("Current pull requests in batch:")
    for pr in res.pull_requests:
        click.echo(f"  - {pr}")
