import click

from obs_flow_cli.types import PR_ID


@click.command(name="clear-needinfo")
@click.argument("pull_request_id", type=PR_ID)
@click.option("-m", "--message", required=True, help="The explanation or answer to the requested info")
@click.option("--override", is_flag=True, help="Override someone else's review")
def cli(pull_request_id: str, message: str, override: bool) -> None:
    """Clear needinfo state on pull request reviews."""

    from obs_flow_client import pr_review_clear_needinfo
    from obs_flow_common.messages import PRReviewClearNeedInfoRequest
    from ..helpers import get_connection, get_config
    from ..output.review import ReviewRenderer

    if not message.strip():
        raise click.BadParameter("Message cannot be empty.", param_hint="--message")

    req = PRReviewClearNeedInfoRequest(
        pull_request_id=pull_request_id,
        message=message,
        override=override,
    )
    with get_connection() as conn:
        res = pr_review_clear_needinfo(conn, req)

    config = get_config()

    renderer = ReviewRenderer(res.review)
    renderer.render(fmt=config.output, verbose=config.verbose)
