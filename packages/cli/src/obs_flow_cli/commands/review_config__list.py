import click


@click.command(name="list")
@click.option("--project", required=True, help="The name of the project.")
@click.option("--type", type=click.Choice(["project", "package", "staging"]), help="Optional configuration type to filter by.")
def cli(project: str, type: str | None) -> None:
    """List review configurations."""

    import os
    from obs_flow_client import list_review_configs
    from obs_flow_common.messages import ReviewConfigListRequest
    from ..helpers import get_connection
    from ..output.review_config import ReviewConfigRenderer

    req = ReviewConfigListRequest(
        project=project,
        type=type,
    )
    with get_connection() as conn:
        res = list_review_configs(conn, req)

    if not res.data:
        click.echo("No review configurations found.", err=True)
        return

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewConfigRenderer(res.data)
    renderer.render(fmt=output, verbose=verbose)
