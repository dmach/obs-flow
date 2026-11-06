import click


@click.command(name="list")
@click.option("--name", help="Filter projects by name.")
@click.option("--org", help="Filter projects by organization.")
@click.option(
    "--workflow-type",
    type=click.Choice(["direct", "staging"]),
    help="Filter projects by workflow type.",
)
def cli(name: str | None, org: str | None, workflow_type: str | None) -> None:
    """List projects."""

    from obs_flow_client import project_list
    from obs_flow_common.messages import ProjectListRequest
    from ..helpers import get_connection, get_config
    from ..output.project import ProjectRenderer

    req = ProjectListRequest(name=name, org=org, workflow_type=workflow_type)
    with get_connection() as conn:
        res = project_list(conn, req)

    if not res.projects:
        click.echo("No projects found.", err=True)
        return

    config = get_config()

    renderer = ProjectRenderer(res.projects)
    renderer.render(fmt=config.output, verbose=config.verbose)
