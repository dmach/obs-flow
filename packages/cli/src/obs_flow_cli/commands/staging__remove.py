import click

from obs_flow_cli.types import PR_ID


@click.command(name="remove")
@click.argument("staging_id", type=click.INT)
@click.argument("pull_request_ids", type=PR_ID, nargs=-1, required=True)
def cli(staging_id: int, pull_request_ids: tuple[str, ...]) -> None:
    """Remove pull requests from a staging batch."""

    from obs_flow_client import remove_from_staging
    from obs_flow_common.messages import StagingRemoveRequest

    from obs_flow_cli.helpers import get_connection

    req = StagingRemoveRequest(
        id=staging_id,
        pull_request_ids=list(pull_request_ids),
    )

    with get_connection() as conn:
        res = remove_from_staging(conn, req)

    click.echo(f"Successfully removed pull requests from staging batch {click.style(str(res.id), bold=True)}.")
    click.echo("Current pull requests in batch:")
    if not res.pull_requests:
        click.echo("  No pull requests included.")
    else:
        for pr in res.pull_requests:
            click.echo(f"  - {pr}")
