import click


@click.command(name="remove")
@click.option("--project", required=True, help="The name of the project.")
@click.option("--type", required=True, type=click.Choice(["project", "package", "staging"]), help="The configuration type.")
@click.option("--user", help="The reviewer username.")
@click.option("--group", help="The reviewer group name.")
@click.option("--role", help="The dynamic reviewer role.")
def cli(project: str, type: str, user: str | None, group: str | None, role: str | None) -> None:
    """Remove a review configuration."""

    import os
    from obs_flow_client import remove_review_config
    from obs_flow_common.messages import ReviewConfigRemoveRequest
    from ..helpers import get_connection
    from ..output.review_config import ReviewConfigRenderer

    # exactly one of user, group, or role must be provided
    options = [user, group, role]
    provided_count = sum(1 for opt in options if opt is not None)
    if provided_count != 1:
        raise click.UsageError("Exactly one of --user, --group, or --role must be provided.")

    reviewer = ""
    if user:
        reviewer = user
    elif group:
        reviewer = f"@{group}"
    elif role:
        reviewer = f"role:{role}"

    req = ReviewConfigRemoveRequest(
        project=project,
        type=type,
        reviewer=reviewer,
    )
    with get_connection() as conn:
        res = remove_review_config(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = ReviewConfigRenderer([res.data])
    renderer.render(fmt=output, verbose=verbose)
