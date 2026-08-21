import click


@click.command(name="list")
def cli() -> None:
    """List git mappings."""

    import os
    from obs_flow_client import list_git_mappings
    from obs_flow_common.messages import GitMappingListRequest
    from ..helpers import get_connection
    from ..output.git_mapping import GitMappingRenderer

    req = GitMappingListRequest()
    with get_connection() as conn:
        res = list_git_mappings(conn, req)

    if not res.mappings:
        click.echo("No git mappings found.", err=True)
        return

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = GitMappingRenderer(res.mappings)
    renderer.render(fmt=output, verbose=verbose)
