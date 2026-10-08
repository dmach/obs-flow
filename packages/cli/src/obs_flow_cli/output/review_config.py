from typing import Any
from .common import Field, Renderer
from .formatters import format_reviewer_dto, get_reviewer_id


class ReviewConfigRenderer(Renderer):
    id_field = lambda item: f"{get_reviewer_id(item.reviewer)} ({item.type})"

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
