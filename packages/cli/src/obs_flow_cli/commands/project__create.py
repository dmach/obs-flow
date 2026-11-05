import click


@click.command(name="create")
@click.argument("name")
@click.option("--org", help="Organization name.")
@click.option("--branch", "branch_name", help="Branch name.")
@click.option(
    "--workflow-type",
    type=click.Choice(["direct", "staging"]),
    default="direct",
    help="Workflow type.",
)
def cli(name: str, org: str | None, branch_name: str | None, workflow_type: str) -> None:
    """Create a project."""

    from obs_flow_client import project_create
    from obs_flow_common.messages import ProjectCreateRequest
    from ..helpers import get_connection, get_config
    from ..output.project import ProjectRenderer

    req = ProjectCreateRequest(
        name=name,
        org=org,
        branch_name=branch_name,
        workflow_type=workflow_type,
    )
    with get_connection() as conn:
        res = project_create(conn, req)

    config = get_config()

    renderer = ProjectRenderer(res.project)
    renderer.render(fmt=config.output, verbose=config.verbose)
