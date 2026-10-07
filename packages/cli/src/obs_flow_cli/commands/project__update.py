import click


@click.command(name="update")
@click.argument("name", required=False)
@click.option("--name", "name_opt", help="The name of the project to update.")
@click.option("--project", "project_opt", help="The name of the project to update.")
@click.option("--workflow-type", type=click.Choice(["direct", "staging"]), help="Set the workflow type for the project.")
def cli(name: str | None, name_opt: str | None, project_opt: str | None, workflow_type: str | None) -> None:
    """Update a project."""

    project_name = name or name_opt or project_opt
    if not project_name:
        raise click.UsageError("Project name is required.")

    from obs_flow_client import project_update
    from obs_flow_common.messages import ProjectUpdateRequest
    from ..helpers import get_connection, get_config
    from ..output.project import ProjectRenderer

    req = ProjectUpdateRequest(
        name=project_name,
        workflow_type=workflow_type,
    )
    with get_connection() as conn:
        res = project_update(conn, req)

    config = get_config()

    renderer = ProjectRenderer(res.project)
    renderer.render(fmt=config.output, verbose=config.verbose)
