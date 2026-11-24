import pytest

from obs_flow_common.pull_requests import pull_request_build_text_id, pull_request_parse_text_id


def test_pull_request_build_text_id():
    assert pull_request_build_text_id("obs", "obs-studio", 42) == "obs/obs-studio#42"


def test_pull_request_parse_text_id_round_trip():
    text_id = pull_request_build_text_id("test", "repo", 42)
    assert pull_request_parse_text_id(text_id) == ("test", "repo", 42)


@pytest.mark.parametrize(
    "bad",
    ["nope", "", "owner/repo", "owner/repo#", "owner/repo#0abc", "/repo#1", "owner/#1"],
)
def test_pull_request_parse_text_id_rejects_invalid_format(bad):
    with pytest.raises(ValueError, match=f"Invalid pull request ID format: {bad}"):
        pull_request_parse_text_id(bad)


def test_pull_request_parse_text_id_allows_slash_in_repo():
    # Pre-existing contract: only owner is slash-free; repo may contain '/'.
    assert pull_request_parse_text_id("a/b/c#1") == ("a", "b/c", 1)
