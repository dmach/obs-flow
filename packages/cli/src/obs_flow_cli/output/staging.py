from .common import Field, Renderer
from .formatters import format_user_dto


class StagingRenderer(Renderer):
    id = Field(
        label="ID",
        style={"bold": True},
    )
    state = Field(
        label="State",
        style=lambda v: {
            "failed": "red",
        }.get(v),
        formatter=lambda v: v.upper(),
    )
    creator = Field(
        label="Creator",
        formatter=format_user_dto,
    )
    title = Field(
        label="Title",
        skip=Field.skip_none,
    )
    target_project = Field(
        label="Project",
    )
    release_date = Field(
        label="Release Date",
        formatter=Field.format_datetime,
        skip=Field.skip_none,
    )
    embargo_date = Field(
        label="Embargo Date",
        formatter=Field.format_datetime,
        skip=Field.skip_none,
    )
