import click


@click.command(name="show")
@click.argument("name")
def cli(name: str) -> None:
    """Show project details."""

    from obs_flow_client import project_show
    from obs_flow_common.messages import ProjectShowRequest
    from ..helpers import get_connection, get_config
    from ..output.project import ProjectRenderer

    req = ProjectShowRequest(name=name)
    with get_connection() as conn:
        res = project_show(conn, req)

    config = get_config()

    renderer = ProjectRenderer(res.project)
    renderer.render(fmt=config.output, verbose=config.verbose)
