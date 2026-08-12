import re

import click


class PullRequestIDParamType(click.ParamType):
    """
    Custom Click parameter type for validating and parsing Pull Request IDs.

    Expected format: <owner>/<repo>#<number>
    """

    name = "pull-request-id"
    # Regex to match <owner>/<repo>#<number> where owner and repo cannot contain slashes or hashes
    PR_ID_REGEX = re.compile(r"^([^/]+)/([^#]+)#(\d+)$")

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> str:
        if not isinstance(value, str):
            self.fail(f"Expected string, got {type(value).__name__}", param, ctx)

        match = self.PR_ID_REGEX.match(value)
        if not match:
            self.fail(
                f"Invalid pull request ID format '{value}'. Expected format: <owner>/<repo>#<number>",
                param,
                ctx,
            )

        return value


PR_ID = PullRequestIDParamType()
