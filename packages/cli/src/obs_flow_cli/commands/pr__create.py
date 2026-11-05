import click


@click.command(name="create")
@click.option("--target-project", required=True, help="Target project name.")
@click.option("--target-package", help="Target package name.")
@click.option("--author", required=True, help="Author username.")
@click.option("--title", required=True, help="Pull request title.")
@click.option("--source-owner", required=True, help="Source owner (e.g. org or username).")
@click.option("--source-repo", required=True, help="Source repo/package.")
@click.option("--source-branch", required=True, help="Source branch.")
@click.option("--draft", is_flag=True, default=False, help="Create pull request as draft.")
def cli(
    target_project: str,
    target_package: str | None,
    author: str,
    title: str,
    source_owner: str,
    source_repo: str,
    source_branch: str,
    draft: bool,
) -> None:
    """Create a pull request."""

    from obs_flow_client import pr_create
    from obs_flow_common.messages import PRCreateRequest
    from ..helpers import get_connection, get_config
    from ..output.pull_request import PullRequestRenderer

    req = PRCreateRequest(
        target_project=target_project,
        target_package=target_package,
        author=author,
        title=title,
        source_owner=source_owner,
        source_repo=source_repo,
        source_branch=source_branch,
        is_draft=draft,
    )
    with get_connection() as conn:
        res = pr_create(conn, req)

    config = get_config()

    renderer = PullRequestRenderer(res.pull_request)
    renderer.render(fmt=config.output, verbose=config.verbose)
