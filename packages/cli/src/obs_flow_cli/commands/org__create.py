import click


@click.command(name="create")
@click.argument("name")
@click.option("--user", help="Associated username for personal org.")
def cli(name: str, user: str | None) -> None:
    """Create an organization."""

    from obs_flow_client import org_create
    from obs_flow_common.messages import OrgCreateRequest
    from ..helpers import get_connection, get_config
    from ..output.org import OrgRenderer

    req = OrgCreateRequest(name=name, user=user)
    with get_connection() as conn:
        res = org_create(conn, req)

    config = get_config()

    renderer = OrgRenderer(res.org)
    renderer.render(fmt=config.output, verbose=config.verbose)
