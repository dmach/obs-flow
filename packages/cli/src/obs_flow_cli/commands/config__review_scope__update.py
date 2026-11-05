import click


@click.command(name="update")
@click.option("--name", required=True, help="The name of the scope to update.")
@click.option("--include", "include_globs", multiple=True, help="New include glob pattern (can be specified multiple times).")
@click.option("--exclude", "exclude_globs", multiple=True, help="New exclude glob pattern (can be specified multiple times).")
def cli(name: str, include_globs: tuple[str, ...], exclude_globs: tuple[str, ...]) -> None:
    """Update a review scope's globs (the name is the identifier; rename is not supported)."""

    from obs_flow_client import review_scope_update
    from obs_flow_common.messages import ReviewScopeEditRequest
    from ..helpers import get_connection, get_config
    from ..output.review_scope import ReviewScopeRenderer

    if not include_globs and not exclude_globs:
        raise click.UsageError("At least one of --include or --exclude must be provided.")

    req = ReviewScopeEditRequest(
        name=name,
        include_globs=list(include_globs) if include_globs else None,
        exclude_globs=list(exclude_globs) if exclude_globs else None,
    )
    with get_connection() as conn:
        res = review_scope_edit(conn, req)

    config = get_config()

    renderer = ReviewScopeRenderer(res.scope)
    renderer.render(fmt=config.output, verbose=config.verbose)
