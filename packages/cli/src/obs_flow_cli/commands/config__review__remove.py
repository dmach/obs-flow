import click


@click.command(name="remove")
@click.option("--project", required=True, help="The name of the project.")
@click.option("--type", required=True, type=click.Choice(["project", "package", "staging"]), help="The configuration type.")
@click.option("--user", help="The reviewer username.")
@click.option("--group", help="The reviewer group name.")
@click.option("--role", help="The dynamic reviewer role.")
def cli(project: str, type: str, user: str | None, group: str | None, role: str | None) -> None:
    """Remove a review configuration."""

    from obs_flow_client import review_config_remove
    from obs_flow_common.messages import ReviewConfigRemoveRequest
    from ..helpers import get_connection, get_config
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
        res = review_config_remove(conn, req)

    config = get_config()

    renderer = ReviewConfigRenderer([res.data])
    renderer.render(fmt=config.output, verbose=config.verbose)
