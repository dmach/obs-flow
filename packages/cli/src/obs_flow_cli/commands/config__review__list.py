import click


@click.command(name="list")
@click.option("--project", required=True, help="The name of the project.")
@click.option("--type", type=click.Choice(["project", "package", "staging"]), help="Optional configuration type to filter by.")
def cli(project: str, type: str | None) -> None:
    """List review configurations."""

    from obs_flow_client import review_config_list
    from obs_flow_common.messages import ReviewConfigListRequest
    from ..helpers import get_connection, get_config
    from ..output.review_config import ReviewConfigRenderer

    req = ReviewConfigListRequest(
        project=project,
        type=type,
    )
    with get_connection() as conn:
        res = review_config_list(conn, req)

    if not res.data:
        click.echo("No review configurations found.", err=True)
        return

    config = get_config()

    renderer = ReviewConfigRenderer(res.data)
    renderer.render(fmt=config.output, verbose=config.verbose)
