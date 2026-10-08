import json
from datetime import datetime
from unittest.mock import patch

import click
import msgspec
import pytest

from obs_flow_cli.output.common import Field, Renderer


class DummyModel(msgspec.Struct):
    id: int
    name: str
    tags: list[str]
    created_at: str | None = None
    is_active: bool | None = None
    secret: str | None = None


class DummyRenderer(Renderer):
    id = Field(label="ID", style={"bold": True})
    name = Field()  # Should default to "Name"
    tags = Field(label="Tags", formatter=lambda v: ", ".join(v))
    created_at = Field(label="Created", formatter=Field.format_datetime)
    is_active = Field(label="Active", formatter=Field.format_yes_no, style=lambda v: "green" if v else "red")
    secret = Field(label="Secret", verbose_only=True)


def test_field_format_datetime():
    assert Field.format_datetime(None) == ""
    assert Field.format_datetime(datetime(2023, 1, 1, 12, 0, 0)) == "2023-01-01 12:00:00"
    assert Field.format_datetime("2023-01-01T12:00:00") == "2023-01-01 12:00:00"


def test_field_format_yes_no():
    assert Field.format_yes_no(True) == "yes"
    assert Field.format_yes_no(False) == "no"
    assert Field.format_yes_no("1") == "yes"
    assert Field.format_yes_no("yes") == "yes"
    assert Field.format_yes_no("true") == "yes"
    assert Field.format_yes_no("on") == "yes"
    assert Field.format_yes_no("0") == "no"
    assert Field.format_yes_no("no") == "no"
    assert Field.format_yes_no("false") == "no"
    assert Field.format_yes_no("off") == "no"
    assert Field.format_yes_no("something else") == "yes"  # fallback to bool(value)


def test_renderer_text():
    data = DummyModel(id=42, name="test", tags=["a", "b"], created_at="2023-01-01T12:00:00", is_active=True)
    renderer = DummyRenderer(data)

    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")

        # Verify click.echo calls
        mock_echo.assert_any_call("ID      : \x1b[1m42\x1b[0m")
        mock_echo.assert_any_call("Name    : test")
        mock_echo.assert_any_call("Tags    : a, b")
        mock_echo.assert_any_call("Created : 2023-01-01 12:00:00")
        mock_echo.assert_any_call("Active  : \x1b[32myes\x1b[0m")

        # Secret should not be shown (verbose_only=True and verbose=False)
        for call in mock_echo.call_args_list:
            assert "Secret" not in call[0][0]


def test_renderer_text_verbose():
    data = DummyModel(id=42, name="test", tags=[], secret="hidden")
    renderer = DummyRenderer(data)

    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text", verbose=True)
        mock_echo.assert_any_call("Secret  : hidden")


def test_renderer_text_list():
    data = [
        DummyModel(id=1, name="test1", tags=[]),
        DummyModel(id=2, name="test2", tags=[]),
    ]
    renderer = DummyRenderer(data)

    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")

        mock_echo.assert_any_call("ID      : \x1b[1m1\x1b[0m")
        mock_echo.assert_any_call("Name    : test1")
        mock_echo.assert_any_call("---")
        mock_echo.assert_any_call("ID      : \x1b[1m2\x1b[0m")
        mock_echo.assert_any_call("Name    : test2")


def test_renderer_json(capsys):
    data = DummyModel(id=42, name="test", tags=["a", "b"])
    renderer = DummyRenderer(data)
    renderer.render(fmt="json")
    captured = capsys.readouterr()

    parsed = json.loads(captured.out)
    assert parsed["id"] == 42
    assert parsed["name"] == "test"
    assert parsed["tags"] == ["a", "b"]


def test_renderer_json_list(capsys):
    data = [
        DummyModel(id=1, name="test1", tags=[]),
        DummyModel(id=2, name="test2", tags=[]),
    ]
    renderer = DummyRenderer(data)
    renderer.render(fmt="json")
    captured = capsys.readouterr()

    parsed = json.loads(captured.out)
    assert len(parsed) == 2
    assert parsed[0]["id"] == 1
    assert parsed[1]["id"] == 2


def test_review_config_renderer():
    from obs_flow_cli.output.review_config import ReviewConfigRenderer
    from obs_flow_common.messages import ReviewConfigDTO, PersonReviewerDTO, GroupReviewerDTO

    # with depends_on
    config1 = ReviewConfigDTO(
        id=1,
        project="openSUSE:Factory",
        type="project",
        reviewer=PersonReviewerDTO(username="darix", full_name=None, email=None, is_active=True),
        depends_on=[
            PersonReviewerDTO(username="reviewer1", full_name=None, email=None, is_active=True),
            PersonReviewerDTO(username="reviewer2", full_name=None, email=None, is_active=True),
        ]
    )
    renderer = ReviewConfigRenderer(config1)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("ID         : \x1b[1m1\x1b[0m")
        mock_echo.assert_any_call("Project    : openSUSE:Factory")
        mock_echo.assert_any_call("Type       : project")
        mock_echo.assert_any_call("Reviewer   : \x1b[1mdarix\x1b[0m")
        mock_echo.assert_any_call("Depends on : reviewer1, reviewer2")

    # without depends_on (empty list)
    config2 = ReviewConfigDTO(
        id=2,
        project="openSUSE:Factory",
        type="project",
        reviewer=PersonReviewerDTO(username="darix", full_name=None, email=None, is_active=True),
        depends_on=[]
    )
    renderer = ReviewConfigRenderer(config2)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("ID         : \x1b[1m2\x1b[0m")
        mock_echo.assert_any_call("Project    : openSUSE:Factory")
        mock_echo.assert_any_call("Type       : project")
        mock_echo.assert_any_call("Reviewer   : \x1b[1mdarix\x1b[0m")
        # ensure "Depends on" is NOT in any of the calls
        for call in mock_echo.call_args_list:
            assert "Depends on" not in call[0][0]

    # detailed person reviewer
    config3 = ReviewConfigDTO(
        id=3,
        project="openSUSE:Factory",
        type="project",
        reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
        depends_on=[]
    )
    renderer = ReviewConfigRenderer(config3)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("Reviewer   : \x1b[1mdarix (Marcus Rueckert <mrueckert@suse.com>)\x1b[0m")

    # detailed group reviewer
    config4 = ReviewConfigDTO(
        id=4,
        project="openSUSE:Factory",
        type="project",
        reviewer=GroupReviewerDTO(name="opensuse-review-team", email="review-team@opensuse.org"),
        depends_on=[]
    )
    renderer = ReviewConfigRenderer(config4)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("Reviewer   : \x1b[1m@opensuse-review-team (<review-team@opensuse.org>)\x1b[0m")


def test_review_renderer():
    from obs_flow_cli.output.review import ReviewRenderer
    from obs_flow_common.messages import ReviewDetail, PersonReviewerDTO, UserDTO

    detail = ReviewDetail(
        reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
        state="accepted",
        actor=UserDTO(username="dimstar", full_name="Dominique Leuenberger", email="dimstar@opensuse.org", is_active=True),
        when="2023-01-01T12:00:00",
        why="Looks good",
    )
    renderer = ReviewRenderer(detail)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("Reviewer : \x1b[1mdarix (Marcus Rueckert <mrueckert@suse.com>)\x1b[0m")
        mock_echo.assert_any_call("State    : \x1b[32mACCEPTED\x1b[0m")
        mock_echo.assert_any_call("Actor    : dimstar (Dominique Leuenberger <dimstar@opensuse.org>)")
        mock_echo.assert_any_call("Date     : 2023-01-01 12:00:00")
        mock_echo.assert_any_call("Reason   : Looks good")


def test_staging_renderer():
    from obs_flow_cli.output.staging import StagingRenderer
    from obs_flow_common.messages import StagingResponse, UserDTO

    response = StagingResponse(
        id=1,
        state="failed",
        creator=UserDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
        title="Staging batch 1",
        target_project="openSUSE:Factory",
        pull_requests=["suse/obs-flow#123"],
        embargo_date="2023-01-01T12:00:00",
        release_date="2023-01-02T12:00:00",
    )
    renderer = StagingRenderer(response)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("ID           : \x1b[1m1\x1b[0m")
        mock_echo.assert_any_call("State        : \x1b[31mFAILED\x1b[0m")
        mock_echo.assert_any_call("Creator      : darix (Marcus Rueckert <mrueckert@suse.com>)")
        mock_echo.assert_any_call("Title        : Staging batch 1")
        mock_echo.assert_any_call("Project      : openSUSE:Factory")
        mock_echo.assert_any_call("Release Date : 2023-01-02 12:00:00")
        mock_echo.assert_any_call("Embargo Date : 2023-01-01 12:00:00")


def test_git_mapping_renderer():
    from obs_flow_cli.output.git_mapping import GitMappingRenderer
    from obs_flow_common.messages import GitMappingDetail

    # Project-only mapping
    detail = GitMappingDetail(
        id=1,
        owner="openSUSE",
        repo="osc",
        branch="master",
        project="openSUSE:Factory",
        package=None,
    )
    renderer = GitMappingRenderer(detail)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("ID         : \x1b[1m1\x1b[0m")
        mock_echo.assert_any_call("Owner      : openSUSE")
        mock_echo.assert_any_call("Repository : osc")
        mock_echo.assert_any_call("Branch     : \x1b[32mmaster\x1b[0m")
        mock_echo.assert_any_call("Project    : openSUSE:Factory")
        # package is None and has skip=Field.skip_none, so it shouldn't be in the output
        for call in mock_echo.call_args_list:
            assert "Package" not in call[0][0]

    # Package-based mapping (should render both project and package)
    detail_pkg = GitMappingDetail(
        id=2,
        owner="openSUSE",
        repo="osc",
        branch="master",
        project="openSUSE:Factory",
        package="osc",
    )
    renderer_pkg = GitMappingRenderer(detail_pkg)
    with patch("click.echo") as mock_echo:
        renderer_pkg.render(fmt="text")
        mock_echo.assert_any_call("ID         : \x1b[1m2\x1b[0m")
        mock_echo.assert_any_call("Owner      : openSUSE")
        mock_echo.assert_any_call("Repository : osc")
        mock_echo.assert_any_call("Branch     : \x1b[32mmaster\x1b[0m")
        mock_echo.assert_any_call("Project    : openSUSE:Factory")
        mock_echo.assert_any_call("Package    : osc")


def test_project_renderer():
    from obs_flow_cli.output.project import ProjectRenderer
    from obs_flow_common.messages import ProjectDetail

    detail = ProjectDetail(
        id=1,
        name="openSUSE:Factory",
        workflow_type="staging",
    )
    renderer = ProjectRenderer(detail)
    with patch("click.echo") as mock_echo:
        renderer.render(fmt="text")
        mock_echo.assert_any_call("ID            : \x1b[1m1\x1b[0m")
        mock_echo.assert_any_call("Name          : openSUSE:Factory")
        mock_echo.assert_any_call("Workflow Type : \x1b[36mstaging\x1b[0m")


def test_renderer_id():
    class Item:
        def __init__(self, id, name, owner, repo):
            self.id = id
            self.name = name
            self.owner = owner
            self.repo = repo

    items = [
        Item(1, "proj1", "org", "repo1"),
        Item(2, "proj2", "org", "repo2"),
    ]

    # Test default id_field ("id")
    class DefaultRenderer(Renderer):
        pass

    with patch("click.echo") as mock_echo:
        DefaultRenderer(items).render(fmt="id")
        assert mock_echo.call_args_list == [
            (( "1", ), {}),
            (( "2", ), {}),
        ]

    # Test custom string id_field ("name")
    class NameRenderer(Renderer):
        id_field = "name"

    with patch("click.echo") as mock_echo:
        NameRenderer(items).render(fmt="id")
        assert mock_echo.call_args_list == [
            (( "proj1", ), {}),
            (( "proj2", ), {}),
        ]

    # Test callable/composite id_field
    class CompositeRenderer(Renderer):
        id_field = lambda item: f"{item.owner}/{item.repo}"

    with patch("click.echo") as mock_echo:
        CompositeRenderer(items).render(fmt="id")
        assert mock_echo.call_args_list == [
            (( "org/repo1", ), {}),
            (( "org/repo2", ), {}),
        ]


def test_get_reviewer_id():
    from obs_flow_cli.output.formatters import get_reviewer_id
    from obs_flow_common.messages import PersonReviewerDTO, GroupReviewerDTO, DynamicRoleReviewerDTO

    person = PersonReviewerDTO(username="alice", full_name="Alice Smith", email="alice@example.com", is_active=True)
    assert get_reviewer_id(person) == "alice"

    group = GroupReviewerDTO(name="release-team", email=None)
    assert get_reviewer_id(group) == "@release-team"

    role = DynamicRoleReviewerDTO(role="maintainer")
    assert get_reviewer_id(role) == "role:maintainer"


def test_bookmark_renderer_id():
    from obs_flow_cli.output.bookmark import BookmarkRenderer
    from obs_flow_common.messages import BookmarkDTO

    bookmark = BookmarkDTO(id=42, name="my-bookmark", url="https://example.com")
    with patch("click.echo") as mock_echo:
        BookmarkRenderer(bookmark).render(fmt="id")
        assert mock_echo.call_args_list == [
            (("my-bookmark",), {}),
        ]


def test_review_renderer_id():
    from obs_flow_cli.output.review import ReviewRenderer
    from obs_flow_common.messages import ReviewDetail, PersonReviewerDTO, GroupReviewerDTO

    reviews = [
        ReviewDetail(
            reviewer=PersonReviewerDTO(username="alice", full_name="Alice", email=None, is_active=True),
            state="accepted",
        ),
        ReviewDetail(
            reviewer=GroupReviewerDTO(name="security", email=None),
            state="pending",
        ),
    ]

    with patch("click.echo") as mock_echo:
        ReviewRenderer(reviews).render(fmt="id")
        assert mock_echo.call_args_list == [
            (("alice (ACCEPTED)",), {}),
            (("@security (PENDING)",), {}),
        ]
