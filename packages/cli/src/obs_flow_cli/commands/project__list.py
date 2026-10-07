import click


@click.command(name="list")
def cli() -> None:
    """List projects."""

    from obs_flow_client import project_list
    from obs_flow_common.messages import ProjectListRequest
    from ..helpers import get_connection, get_config
    from ..output.project import ProjectRenderer

    req = ProjectListRequest()
    with get_connection() as conn:
        res = project_list(conn, req)

    if not res.projects:
        click.echo("No projects found.", err=True)
        return

    config = get_config()

    renderer = ProjectRenderer(res.projects)
    renderer.render(fmt=config.output, verbose=config.verbose)
