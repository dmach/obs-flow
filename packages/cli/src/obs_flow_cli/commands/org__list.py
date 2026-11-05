import click


@click.command(name="list")
def cli() -> None:
    """List organizations."""

    from obs_flow_client import org_list
    from obs_flow_common.messages import OrgListRequest
    from ..helpers import get_connection, get_config
    from ..output.org import OrgRenderer

    req = OrgListRequest()
    with get_connection() as conn:
        res = org_list(conn, req)

    if not res.orgs:
        click.echo("No organizations found.", err=True)
        return

    config = get_config()

    renderer = OrgRenderer(res.orgs)
    renderer.render(fmt=config.output, verbose=config.verbose)
