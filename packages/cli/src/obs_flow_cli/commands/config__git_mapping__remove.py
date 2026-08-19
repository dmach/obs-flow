import click


@click.command(name="remove")
@click.option("--id", required=True, type=int, help="The ID of the git mapping to remove.")
def cli(id: int) -> None:
    """Remove a git mapping."""

    from obs_flow_client import remove_git_mapping
    from obs_flow_common.messages import GitMappingRemoveRequest
    from ..helpers import get_connection

    req = GitMappingRemoveRequest(id=id)
    with get_connection() as conn:
        res = remove_git_mapping(conn, req)

    if res.success:
        click.echo(f"Successfully removed git mapping with ID {id}.")
    else:
        click.echo(f"Failed to remove git mapping with ID {id} (not found).", err=True)
        raise click.ClickException(f"Git mapping with ID {id} not found.")
