import click


@click.command(name="import")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--force", is_flag=True, help="Overwrite existing bookmarks with the same name")
def cli(file_path: str, force: bool) -> None:
    """Import bookmarks from a JSON file."""

    import json
    from obs_flow_client import import_bookmarks
    from obs_flow_common.messages import BookmarkImportRequest, BookmarkAddRequest
    from ..helpers import get_connection

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to read or parse JSON file: {e}")

    if not isinstance(data, list):
        raise click.ClickException("Invalid JSON format: expected a list of bookmarks.")

    items = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict) or "name" not in item or "url" not in item:
            raise click.ClickException(f"Invalid bookmark item at index {idx}: each item must have 'name' and 'url' fields.")
        items.append(BookmarkAddRequest(name=item["name"], url=item["url"]))

    req = BookmarkImportRequest(items=items, force=force)

    with get_connection() as conn:
        res = import_bookmarks(conn, req)

    click.echo(f"Successfully imported {res.imported_count} bookmark(s) and updated {res.updated_count} bookmark(s).")
