import click


@click.command(name="list")
def cli() -> None:
    """List all review scopes."""

    from obs_flow_client import review_scope_list
    from obs_flow_common.messages import ReviewScopeListRequest
    from ..helpers import get_connection, get_config
    from ..output.review_scope import ReviewScopeRenderer

    req = ReviewScopeListRequest()
    with get_connection() as conn:
        res = review_scope_list(conn, req)

    if not res.scopes:
        click.echo("No review scopes found.", err=True)
        return

    config = get_config()

    renderer = ReviewScopeRenderer(res.scopes)
    renderer.render(fmt=config.output, verbose=config.verbose)
