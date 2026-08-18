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

