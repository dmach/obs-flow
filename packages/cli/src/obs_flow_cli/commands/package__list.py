import click


@click.command(name="list")
@click.option("--project", help="Filter packages by project name.")
def cli(project: str | None) -> None:
    """List packages."""

    from obs_flow_client import package_list
    from obs_flow_common.messages import PackageListRequest
    from ..helpers import get_connection, get_config
    from ..output.package import PackageRenderer

    req = PackageListRequest(project=project)
    with get_connection() as conn:
        res = package_list(conn, req)

    if not res.packages:
        click.echo("No packages found.", err=True)
        return

    config = get_config()

    renderer = PackageRenderer(res.packages)
    renderer.render(fmt=config.output, verbose=config.verbose)
