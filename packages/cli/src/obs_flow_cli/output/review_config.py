from typing import Any
from .common import Field, Renderer


class ReviewConfigRenderer(Renderer):
    id = Field(
        label="ID",
        style={"bold": True},
    )
    project = Field(
        label="Project",
    )
    type = Field(
        label="Type",
    )
    reviewer = Field(
        label="Reviewer",
        style={"bold": True},
    )
    depends_on = Field(
        label="Depends on",
        formatter=lambda v: ", ".join(v),
        skip=Field.skip_empty,
    )
