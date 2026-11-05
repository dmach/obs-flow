from unittest.mock import patch
from click.testing import CliRunner
import pytest

from obs_flow_cli.cli import main
from obs_flow_common.messages import (
    ProjectDetail,
    ProjectListResponse,
    ProjectUpdateResponse,
)


def test_cli_project_list():
    runner = CliRunner()
    mock_projects = [
        ProjectDetail(
            id=1,
            name="openSUSE:Factory",
            workflow_type="staging",
        ),
        ProjectDetail(
            id=2,
            name="openSUSE:Leap:16.0",
            workflow_type="direct",
        ),
    ]
    with patch("obs_flow_client.project_list") as mock_list:
        mock_list.return_value = ProjectListResponse(projects=mock_projects)
        result = runner.invoke(main, ["project", "list"])

    assert result.exit_code == 0
    assert "ID            : 1" in result.output
    assert "Name          : openSUSE:Factory" in result.output
    assert "Workflow Type : staging" in result.output
    assert "ID            : 2" in result.output
    assert "Name          : openSUSE:Leap:16.0" in result.output
    assert "Workflow Type : direct" in result.output


def test_cli_project_update():
    runner = CliRunner()
    mock_project = ProjectDetail(
        id=2,
        name="openSUSE:Leap:16.0",
        workflow_type="staging",
    )
    with patch("obs_flow_client.project_update") as mock_update:
        mock_update.return_value = ProjectUpdateResponse(project=mock_project)
        result = runner.invoke(
            main,
            [
                "project",
                "update",
                "openSUSE:Leap:16.0",
                "--workflow-type",
                "staging",
            ],
        )

    assert result.exit_code == 0
    assert "ID            : 2" in result.output
    assert "Name          : openSUSE:Leap:16.0" in result.output
    assert "Workflow Type : staging" in result.output


def test_cli_project_update_missing_name():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "project",
            "update",
            "--workflow-type",
            "staging",
        ],
    )
    assert result.exit_code != 0
    assert "Project name is required" in result.output


def test_cli_org_list_and_create():
    from obs_flow_common.messages import OrgDetail, OrgListResponse, OrgCreateResponse

    runner = CliRunner()
    with patch("obs_flow_client.org_list") as mock_list:
        mock_list.return_value = OrgListResponse(
            orgs=[OrgDetail(id=1, name="openSUSE", is_personal=False, user=None)]
        )
        res = runner.invoke(main, ["org", "list"])
        assert res.exit_code == 0
        assert "openSUSE" in res.output

    with patch("obs_flow_client.org_create") as mock_create:
        mock_create.return_value = OrgCreateResponse(
            org=OrgDetail(id=2, name="~tux", is_personal=True, user="tux")
        )
        res = runner.invoke(main, ["org", "create", "~tux", "--user", "tux"])
        assert res.exit_code == 0
        assert "~tux" in res.output


def test_cli_project_create():
    from obs_flow_common.messages import ProjectDetail, ProjectCreateResponse

    runner = CliRunner()
    with patch("obs_flow_client.project_create") as mock_create:
        mock_create.return_value = ProjectCreateResponse(
            project=ProjectDetail(
                id=1,
                name="openSUSE:Factory",
                workflow_type="staging",
                org="openSUSE",
                branch_name="factory",
            )
        )
        res = runner.invoke(
            main,
            [
                "project",
                "create",
                "openSUSE:Factory",
                "--org",
                "openSUSE",
                "--branch",
                "factory",
                "--workflow-type",
                "staging",
            ],
        )
        assert res.exit_code == 0
        assert "openSUSE:Factory" in res.output
        assert "factory" in res.output


def test_cli_package_list_and_create():
    from obs_flow_common.messages import PackageDetail, PackageListResponse, PackageCreateResponse

    runner = CliRunner()
    with patch("obs_flow_client.package_list") as mock_list:
        mock_list.return_value = PackageListResponse(
            packages=[PackageDetail(id=1, project="openSUSE:Factory", name="bash", forked_from=None)]
        )
        res = runner.invoke(main, ["package", "list", "--project", "openSUSE:Factory"])
        assert res.exit_code == 0
        assert "bash" in res.output

    with patch("obs_flow_client.package_create") as mock_create:
        mock_create.return_value = PackageCreateResponse(
            package=PackageDetail(
                id=2,
                project="home:contributor",
                name="bash",
                forked_from="openSUSE:Factory/bash",
            )
        )
        res = runner.invoke(
            main,
            [
                "package",
                "create",
                "home:contributor",
                "bash",
                "--fork-from-project",
                "openSUSE:Factory",
                "--fork-from-package",
                "bash",
            ],
        )
        assert res.exit_code == 0
        assert "home:contributor" in res.output
        assert "openSUSE:Factory/bash" in res.output


def test_cli_pr_create():
    from obs_flow_common.messages import PRDetail, PRCreateResponse, UserDTO

    runner = CliRunner()
    with patch("obs_flow_client.pr_create") as mock_create:
        mock_create.return_value = PRCreateResponse(
            pull_request=PRDetail(
                id="openSUSE/bash#1",
                title="Update bash",
                state="open",
                is_draft=False,
                is_mergeable=True,
                author=UserDTO(username="contributor"),
                latest_revision=1,
                head_sha="abcdef",
                base_sha="123456",
            )
        )
        res = runner.invoke(
            main,
            [
                "pr",
                "create",
                "--target-project",
                "openSUSE:Factory",
                "--target-package",
                "bash",
                "--author",
                "contributor",
                "--title",
                "Update bash",
                "--source-owner",
                "~contributor",
                "--source-repo",
                "bash",
                "--source-branch",
                "feature",
            ],
        )
        assert res.exit_code == 0
        assert "openSUSE/bash#1" in res.output

