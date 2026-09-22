import click


@click.command(name="show")
@click.argument("staging_id", type=click.INT)
def cli(staging_id: int) -> None:
    """Show staging batch details."""

    import os
    from obs_flow_client import staging_show
    from ..helpers import get_connection
    from ..output.staging import StagingRenderer

    with get_connection() as conn:
        res = staging_show(conn, staging_id)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = StagingRenderer(res)
    renderer.render(fmt=output, verbose=verbose)

    # TODO: use renderer
    click.echo("-" * 40)
    click.echo("Included Pull Requests:")
    if not res.pull_requests:
        click.echo("  No pull requests included.")
    else:
        for pr in res.pull_requests:
            click.echo(f"  - {pr}")
