import click


@click.command(name="edit")
@click.option("--id", required=True, type=int, help="The ID of the git mapping to edit.")
@click.option("--owner", help="The new owner of the repository.")
@click.option("--repo", help="The new repository name.")
@click.option("--branch", help="The new branch name.")
@click.option("--project", help="The new project name.")
@click.option("--package", help="The new package name.")
def cli(
    id: int,
    owner: str | None,
    repo: str | None,
    branch: str | None,
    project: str | None,
    package: str | None,
) -> None:
    """Edit a git mapping."""

    import os
    from obs_flow_client import edit_git_mapping
    from obs_flow_common.messages import GitMappingEditRequest
    from ..helpers import get_connection
    from ..output.git_mapping import GitMappingRenderer

    req = GitMappingEditRequest(
        id=id,
        owner=owner,
        repo=repo,
        branch=branch,
        project=project,
        package=package,
    )
    with get_connection() as conn:
        res = edit_git_mapping(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = GitMappingRenderer(res.mapping)
    renderer.render(fmt=output, verbose=verbose)
