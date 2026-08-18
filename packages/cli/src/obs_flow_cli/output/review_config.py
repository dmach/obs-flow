from typing import Any
from .common import Field, Renderer
from .formatters import format_reviewer_dto


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
        formatter=format_reviewer_dto,
    )
    depends_on = Field(
        label="Depends on",
        formatter=lambda v: ", ".join(format_reviewer_dto(dep) for dep in v),
        skip=Field.skip_empty,
    )
