import click


@click.command(name="add")
@click.option("--owner", required=True, help="The owner of the repository.")
@click.option("--repo", required=True, help="The repository name.")
@click.option("--branch", required=True, help="The branch name.")
@click.option("--project", help="The project name.")
@click.option("--package", help="The package name.")
def cli(owner: str, repo: str, branch: str, project: str | None, package: str | None) -> None:
    """Add a git mapping."""

    if not project and not package:
        raise click.UsageError("Either --project or --package must be specified.")

    if package and not project:
        raise click.UsageError("--project must be specified when --package is provided.")

    import os
    from obs_flow_client import add_git_mapping
    from obs_flow_common.messages import GitMappingAddRequest
    from ..helpers import get_connection
    from ..output.git_mapping import GitMappingRenderer

    req = GitMappingAddRequest(
        owner=owner,
        repo=repo,
        branch=branch,
        project=project,
        package=package,
    )
    with get_connection() as conn:
        res = add_git_mapping(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = GitMappingRenderer(res.mapping)
    renderer.render(fmt=output, verbose=verbose)
