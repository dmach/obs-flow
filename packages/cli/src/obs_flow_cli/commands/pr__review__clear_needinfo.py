import click

from obs_flow_cli.types import PR_ID


@click.command(name="clear-needinfo")
@click.argument("pull_request_id", type=PR_ID)
@click.option("-m", "--message", required=True, help="Mandatory clarification message")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, message: str, override: bool) -> None:
    """Clear needinfo state on pull request reviews."""

    from obs_flow_client import clear_needinfo_review
    from obs_flow_common.messages import PRReviewClearNeedInfoRequest

    from obs_flow_cli.helpers import format_review, get_connection

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = PRReviewClearNeedInfoRequest(
        pull_request_id=pull_request_id,
        message=message,
        override=override,
    )

    with get_connection() as conn:
        res = clear_needinfo_review(conn, req)

    click.echo(f"Pull Request: {click.style(res.pull_request_id, bold=True)}")
    click.echo("=" * 40)
    format_review(res.review)
