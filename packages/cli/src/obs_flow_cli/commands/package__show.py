import click


@click.command(name="show")
@click.argument("project")
@click.argument("name", required=False)
def cli(project: str, name: str | None) -> None:
    """Show package details."""

    if name is None:
        if "/" in project:
            project, name = project.split("/", 1)
        else:
            raise click.UsageError(
                "Specify both project and package name, e.g. 'show <project> <package>' or 'show <project>/<package>'."
            )

    from obs_flow_client import package_show
    from obs_flow_common.messages import PackageShowRequest
    from ..helpers import get_connection, get_config
    from ..output.package import PackageRenderer

    req = PackageShowRequest(project=project, name=name)
    with get_connection() as conn:
        res = package_show(conn, req)

    config = get_config()

    renderer = PackageRenderer(res.package)
    renderer.render(fmt=config.output, verbose=config.verbose)
