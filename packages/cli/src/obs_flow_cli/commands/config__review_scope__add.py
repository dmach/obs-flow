import click


@click.command(name="add")
@click.option("--name", required=True, help="The unique name of the scope.")
@click.option("--include", "include_globs", multiple=True, required=True, help="Include glob pattern (can be specified multiple times).")
@click.option("--exclude", "exclude_globs", multiple=True, help="Exclude glob pattern (can be specified multiple times).")
def cli(name: str, include_globs: tuple[str, ...], exclude_globs: tuple[str, ...]) -> None:
    """Add a new review scope."""

    from obs_flow_client import review_scope_add
    from obs_flow_common.messages import ReviewScopeAddRequest
    from ..helpers import get_connection, get_config
    from ..output.review_scope import ReviewScopeRenderer

    req = ReviewScopeAddRequest(
        name=name,
        include_globs=list(include_globs),
        exclude_globs=list(exclude_globs),
    )
    with get_connection() as conn:
        res = review_scope_add(conn, req)

    config = get_config()

    renderer = ReviewScopeRenderer(res.scope)
    renderer.render(fmt=config.output, verbose=config.verbose)
