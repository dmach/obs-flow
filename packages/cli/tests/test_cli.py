from unittest.mock import patch
from click.testing import CliRunner
import pytest

from obs_flow_cli.cli import main
from obs_flow_common.messages import (
    GitMappingDetail,
    GitMappingListResponse,
    GitMappingAddResponse,
    GitMappingRemoveResponse,
    GitMappingEditResponse,
)


def test_cli_config_git_mapping_list():
    runner = CliRunner()
    mock_mappings = [
        GitMappingDetail(
            id=1,
            owner="openSUSE",
            repo="osc",
            branch="master",
            project="openSUSE:Factory",
            package=None,
        )
    ]
    with patch("obs_flow_client.list_git_mappings") as mock_list:
        mock_list.return_value = GitMappingListResponse(mappings=mock_mappings)
        result = runner.invoke(main, ["config", "git-mapping", "list"])

    assert result.exit_code == 0
    assert "ID         : 1" in result.output
    assert "Owner      : openSUSE" in result.output
    assert "Repository : osc" in result.output
    assert "Branch     : master" in result.output
    assert "Project    : openSUSE:Factory" in result.output


def test_cli_config_git_mapping_add():
    runner = CliRunner()
    mock_mapping = GitMappingDetail(
        id=1,
        owner="openSUSE",
        repo="osc",
        branch="master",
        project="openSUSE:Factory",
        package=None,
    )
    with patch("obs_flow_client.add_git_mapping") as mock_add:
        mock_add.return_value = GitMappingAddResponse(mapping=mock_mapping)
        result = runner.invoke(
            main,
            [
                "config",
                "git-mapping",
                "add",
                "--owner",
                "openSUSE",
                "--repo",
                "osc",
                "--branch",
                "master",
                "--project",
                "openSUSE:Factory",
            ],
        )

    assert result.exit_code == 0
    assert "ID         : 1" in result.output
    assert "Owner      : openSUSE" in result.output


def test_cli_config_git_mapping_add_missing_options():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "config",
            "git-mapping",
            "add",
            "--owner",
            "openSUSE",
            "--repo",
            "osc",
            "--branch",
            "master",
        ],
    )
    assert result.exit_code != 0
    assert "Either --project or --package must be specified" in result.output


def test_cli_config_git_mapping_remove():
    runner = CliRunner()
    with patch("obs_flow_client.remove_git_mapping") as mock_remove:
        mock_remove.return_value = GitMappingRemoveResponse(success=True)
        result = runner.invoke(main, ["config", "git-mapping", "remove", "--id", "1"])

    assert result.exit_code == 0
    assert "Successfully removed git mapping with ID 1" in result.output


def test_cli_config_git_mapping_edit():
    runner = CliRunner()
    mock_mapping = GitMappingDetail(
        id=1,
        owner="openSUSE",
        repo="osc",
        branch="develop",
        project="openSUSE:Factory",
        package=None,
    )
    with patch("obs_flow_client.edit_git_mapping") as mock_edit:
        mock_edit.return_value = GitMappingEditResponse(mapping=mock_mapping)
        result = runner.invoke(
            main,
            [
                "config",
                "git-mapping",
                "edit",
                "--id",
                "1",
                "--branch",
                "develop",
            ],
        )

    assert result.exit_code == 0
    assert "Branch     : develop" in result.output
