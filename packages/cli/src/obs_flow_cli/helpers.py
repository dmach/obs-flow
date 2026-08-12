import os

import click
from obs_flow_client import Connection
from obs_flow_common.messages import ReviewDetail


def get_connection() -> Connection:
    """Returns an initialized Connection to the OBS Flow server."""
    server_url = os.environ.get("OBS_FLOW_SERVER_URL", "http://localhost:8000")
    return Connection(base_url=server_url)


def format_review(review: ReviewDetail) -> None:
    """Prints a single review detail in a clean, formatted way."""
    click.echo(f"Reviewer: {click.style(review.reviewer, fg='cyan', bold=True)}")
    click.echo(
        f"State:    {click.style(review.state.upper(), fg='green' if review.state in ('accepted', 'approved') else 'yellow', bold=True)}"
    )
    if review.actor:
        click.echo(f"Actor:    {review.actor}")
    if review.when:
        click.echo(f"When:     {review.when}")
    if review.why:
        click.echo(f"Why:      {review.why}")
    click.echo("-" * 40)
