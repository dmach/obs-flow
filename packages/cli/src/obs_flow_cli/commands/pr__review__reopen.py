import click

from obs_flow_cli.types import PR_ID


@click.command(name="reopen")
@click.argument("pull_request_id", type=PR_ID)
@click.option("-m", "--message", required=True, help="Mandatory justification message")
@click.option("--reviewer", help="The reviewer (user or @group) to reopen on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, message: str, reviewer: str | None, override: bool) -> None:
    """Reopen a declined pull request review."""

    from obs_flow_client import reopen_review
    from obs_flow_common.messages import PRReviewReopenRequest

    from obs_flow_cli.helpers import format_review, get_connection

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = PRReviewReopenRequest(
        pull_request_id=pull_request_id,
        message=message,
        reviewer=reviewer,
        override=override,
    )

    with get_connection() as conn:
        res = reopen_review(conn, req)

    click.echo(f"Pull Request: {click.style(res.pull_request_id, bold=True)}")
    click.echo("=" * 40)
    format_review(res.review)
