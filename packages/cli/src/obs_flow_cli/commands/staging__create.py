import click


@click.command(name="create")
@click.option("--project", required=True, help="The target project for the staging batch")
@click.option("--title", help="A descriptive title for the staging batch")
@click.option("--embargo-date", help="Planned embargo date (ISO-8601 format)")
@click.option("--release-date", help="Planned release date (ISO-8601 format)")
def cli(project: str, title: str | None, embargo_date: str | None, release_date: str | None) -> None:
    """Create a new staging batch."""

    import os
    from obs_flow_client import create_staging
    from obs_flow_common.messages import StagingCreateRequest
    from ..helpers import get_connection
    from ..output.staging import StagingRenderer

    req = StagingCreateRequest(
        project=project,
        title=title,
        embargo_date=embargo_date,
        release_date=release_date,
    )
    with get_connection() as conn:
        res = create_staging(conn, req)

    verbose = os.getenv("OBS_FLOW_VERBOSE") == "1"
    output = os.getenv("OBS_FLOW_OUTPUT")

    renderer = StagingRenderer(res)
    renderer.render(fmt=output, verbose=verbose)
