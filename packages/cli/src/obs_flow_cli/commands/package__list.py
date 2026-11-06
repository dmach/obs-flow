import click


@click.command(name="list")
@click.option("--project", help="Filter packages by project name.")
@click.option("--name", help="Filter packages by package name.")
def cli(project: str | None, name: str | None) -> None:
    """List packages."""

    from obs_flow_client import package_list
    from obs_flow_common.messages import PackageListRequest
    from ..helpers import get_connection, get_config
    from ..output.package import PackageRenderer

    req = PackageListRequest(project=project, name=name)
    with get_connection() as conn:
        res = package_list(conn, req)

    if not res.packages:
        click.echo("No packages found.", err=True)
        return

    config = get_config()

    renderer = PackageRenderer(res.packages)
    renderer.render(fmt=config.output, verbose=config.verbose)
