import click

from obs_flow_common.pull_requests import pull_request_parse_text_id


class PullRequestIDParamType(click.ParamType):
    """
    Custom Click parameter type for validating and parsing Pull Request IDs.

    Expected format: <owner>/<repo>#<number>
    """

    name = "pull-request-id"

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> str:
        if not isinstance(value, str):
            self.fail(f"Expected string, got {type(value).__name__}", param, ctx)

        try:
            pull_request_parse_text_id(value)
        except ValueError:
            self.fail(
                f"Invalid pull request ID format '{value}'. Expected format: <owner>/<repo>#<number>",
                param,
                ctx,
            )

        return value


PR_ID = PullRequestIDParamType()
