import click


@click.command(name="create")
@click.argument("project")
@click.argument("name")
@click.option("--fork-from-project", help="Source project to fork from.")
@click.option("--fork-from-package", help="Source package to fork from.")
def cli(project: str, name: str, fork_from_project: str | None, fork_from_package: str | None) -> None:
    """Create a package."""

    from obs_flow_client import package_create
    from obs_flow_common.messages import PackageCreateRequest
    from ..helpers import get_connection, get_config
    from ..output.package import PackageRenderer

    req = PackageCreateRequest(
        project=project,
        name=name,
        fork_from_project=fork_from_project,
        fork_from_package=fork_from_package,
    )
    with get_connection() as conn:
        res = package_create(conn, req)

    config = get_config()

    renderer = PackageRenderer(res.package)
    renderer.render(fmt=config.output, verbose=config.verbose)
