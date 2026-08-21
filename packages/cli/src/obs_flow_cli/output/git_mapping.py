from typing import Any
from .common import Field, Renderer


class GitMappingRenderer(Renderer):
    id = Field(
        label="ID",
        style={"bold": True},
    )
    owner = Field(
        label="Owner",
    )
    repo = Field(
        label="Repository",
    )
    branch = Field(
        label="Branch",
        style="green",
    )
    project = Field(
        label="Project",
        skip=Field.skip_none,
    )
    package = Field(
        label="Package",
        skip=Field.skip_none,
    )
