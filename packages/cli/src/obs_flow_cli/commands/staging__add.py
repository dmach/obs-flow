import click

from obs_flow_cli.types import PR_ID


@click.command(name="add")
@click.argument("staging_id", type=click.INT)
@click.argument("pull_request_ids", type=PR_ID, nargs=-1, required=True)
@click.option("--allow-duplicates", is_flag=True, help="Allow adding a PR into staging even if it belongs to another staging already")
def cli(staging_id: int, pull_request_ids: tuple[str, ...], allow_duplicates: bool) -> None:
    """Add pull requests to a staging batch."""

    import os
    from obs_flow_client import add_to_staging
    from obs_flow_common.messages import StagingAddRequest
    from ..helpers import get_connection
    from ..output.staging import StagingRenderer

    req = StagingAddRequest(
        id=staging_id,
        pull_request_ids=list(pull_request_ids),
        allow_duplicates=allow_duplicates,
    )

    with get_connection() as conn:
        res = add_to_staging(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = StagingRenderer(res)
    renderer.render(fmt=output, verbose=verbose)
