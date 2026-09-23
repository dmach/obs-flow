import click


@click.command(name="add")
@click.option("--project", required=True, help="The name of the project.")
@click.option("--type", required=True, type=click.Choice(["project", "package", "staging"]), help="The configuration type.")
@click.option("--user", help="The reviewer username.")
@click.option("--group", help="The reviewer group name.")
@click.option("--role", help="The dynamic reviewer role.")
@click.option("--depends-on", multiple=True, help="Reviewer identifier this configuration depends on (can be specified multiple times).")
def cli(project: str, type: str, user: str | None, group: str | None, role: str | None, depends_on: tuple[str, ...]) -> None:
    """Add or update a review configuration."""

    from obs_flow_client import review_config_add
    from obs_flow_common.messages import ReviewConfigAddRequest
    from ..helpers import get_connection, get_config
    from ..output.review_config import ReviewConfigRenderer

    # exactly one of user, group, or role must be provided
    reviewer_options = [user, group, role]
    provided_count = sum(1 for opt in reviewer_options if opt is not None)
    if provided_count != 1:
        raise click.UsageError("Exactly one of --user, --group, or --role must be provided.")

    if user:
        reviewer = user
    elif group:
        reviewer = f"@{group}"
    else:
        reviewer = f"role:{role}"

    req = ReviewConfigAddRequest(
        project=project,
        type=type,
        reviewer=reviewer,
        depends_on=list(depends_on),
    )
    with get_connection() as conn:
        res = review_config_add(conn, req)

    config = get_config()

    renderer = ReviewConfigRenderer([res.data])
    renderer.render(fmt=config.output, verbose=config.verbose)
