from unittest.mock import patch
from click.testing import CliRunner
import pytest
import json

from obs_flow_cli.cli import main
from obs_flow_common.messages import (
    BookmarkDTO,
    BookmarkListResponse,
    BookmarkAddResponse,
    BookmarkRemoveResponse,
    BookmarkImportResponse,
)


def test_cli_bookmark_list():
    runner = CliRunner()
    mock_bookmarks = [
        BookmarkDTO(
            id=1,
            name="My Filter",
            url="/foo",
        )
    ]
    with patch("obs_flow_client.bookmark_list") as mock_list:
        mock_list.return_value = BookmarkListResponse(bookmarks=mock_bookmarks)
        result = runner.invoke(main, ["config", "bookmark", "list", "--name", "My Filter", "--name-contains", "Filter"])

    assert result.exit_code == 0
    assert "ID   : 1" in result.output
    assert "Name : My Filter" in result.output
    assert "URL  : /foo" in result.output


def test_cli_bookmark_add():
    runner = CliRunner()
    mock_bookmark = BookmarkDTO(
        id=1,
        name="My Filter",
        url="/foo",
    )
    with patch("obs_flow_client.bookmark_add") as mock_add:
        mock_add.return_value = BookmarkAddResponse(bookmark=mock_bookmark)
        result = runner.invoke(main, ["config", "bookmark", "add", "My Filter", "/foo"])

    assert result.exit_code == 0
    assert "ID   : 1" in result.output
    assert "Name : My Filter" in result.output
    assert "URL  : /foo" in result.output


def test_cli_bookmark_remove_success():
    runner = CliRunner()
    with patch("obs_flow_client.bookmark_remove") as mock_remove:
        mock_remove.return_value = BookmarkRemoveResponse(success=True)
        result = runner.invoke(main, ["config", "bookmark", "remove", "My Filter"])

    assert result.exit_code == 0
    assert "Successfully removed bookmark 'My Filter'" in result.output


def test_cli_bookmark_remove_failure():
    runner = CliRunner()
    with patch("obs_flow_client.bookmark_remove") as mock_remove:
        mock_remove.return_value = BookmarkRemoveResponse(success=False)
        result = runner.invoke(main, ["config", "bookmark", "remove", "My Filter"])

    assert result.exit_code != 0
    assert "Failed to remove bookmark 'My Filter'" in result.output


def test_cli_bookmark_show_success():
    runner = CliRunner()
    mock_bookmarks = [
        BookmarkDTO(
            id=1,
            name="My Filter",
            url="/foo",
        )
    ]
    with patch("obs_flow_client.bookmark_list") as mock_list:
        mock_list.return_value = BookmarkListResponse(bookmarks=mock_bookmarks)
        result = runner.invoke(main, ["config", "bookmark", "show", "My Filter"])

    assert result.exit_code == 0
    assert "/foo" in result.output


def test_cli_bookmark_show_not_found():
    runner = CliRunner()
    with patch("obs_flow_client.bookmark_list") as mock_list:
        mock_list.return_value = BookmarkListResponse(bookmarks=[])
        result = runner.invoke(main, ["config", "bookmark", "show", "My Filter"])

    assert result.exit_code != 0
    assert "Bookmark 'My Filter' not found" in result.output


def test_cli_bookmark_import_success(tmp_path):
    runner = CliRunner()
    bookmarks_data = [
        {"name": "B1", "url": "/foo"},
        {"name": "B2", "url": "/bar"},
    ]
    file_path = tmp_path / "bookmarks.json"
    file_path.write_text(json.dumps(bookmarks_data))

    with patch("obs_flow_client.bookmark_import") as mock_import:
        mock_import.return_value = BookmarkImportResponse(imported_count=2, updated_count=0)
        result = runner.invoke(main, ["config", "bookmark", "import", str(file_path)])

    assert result.exit_code == 0
    assert "Successfully imported 2 bookmark(s) and updated 0 bookmark(s)." in result.output


def test_cli_bookmark_import_with_force(tmp_path):
    runner = CliRunner()
    bookmarks_data = [
        {"name": "B1", "url": "/foo"},
    ]
    file_path = tmp_path / "bookmarks.json"
    file_path.write_text(json.dumps(bookmarks_data))

    with patch("obs_flow_client.bookmark_import") as mock_import:
        mock_import.return_value = BookmarkImportResponse(imported_count=0, updated_count=1)
        result = runner.invoke(main, ["config", "bookmark", "import", str(file_path), "--force"])

    assert result.exit_code == 0
    assert "Successfully imported 0 bookmark(s) and updated 1 bookmark(s)." in result.output
