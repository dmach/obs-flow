import click

from obs_flow_cli.types import PR_ID


@click.command(name="remove")
@click.argument("staging_id", type=click.INT)
@click.argument("pull_request_ids", type=PR_ID, nargs=-1, required=True)
def cli(staging_id: int, pull_request_ids: tuple[str, ...]) -> None:
    """Remove pull requests from a staging batch."""

    from obs_flow_client import staging_remove
    from obs_flow_common.messages import StagingRemoveRequest
    from ..helpers import get_connection, get_config
    from ..output.staging import StagingRenderer

    req = StagingRemoveRequest(
        id=staging_id,
        pull_request_ids=list(pull_request_ids),
    )
    with get_connection() as conn:
        res = staging_remove(conn, req)

    config = get_config()

    renderer = StagingRenderer(res)
    renderer.render(fmt=config.output, verbose=config.verbose)
