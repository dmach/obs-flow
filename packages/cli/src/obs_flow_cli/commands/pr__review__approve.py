import click

from obs_flow_cli.types import PR_ID


@click.command(name="approve")
@click.argument("pull_request_id", type=PR_ID)
@click.option("--reviewer", help="The reviewer (user or @group) to approve on behalf of")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, reviewer: str | None, override: bool) -> None:
    """Approve a pull request review."""

    from obs_flow_client import approve_review
    from obs_flow_common.messages import PRReviewApproveRequest

    from obs_flow_cli.helpers import format_review, get_connection

    req = PRReviewApproveRequest(pull_request_id=pull_request_id, reviewer=reviewer, override=override)

    with get_connection() as conn:
        res = approve_review(conn, req)

    click.echo(f"Pull Request: {click.style(res.pull_request_id, bold=True)}")
    click.echo("=" * 40)
    format_review(res.review)
