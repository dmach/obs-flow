from .common import Field, Renderer


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
    )
    title = Field(
        label="Title",
    )
    project = Field(
        label="Project",
    )
    release_date = Field(
        label="Release Date",
        formatter=Field.format_datetime,
    )
    embargo_date = Field(
        label="Embargo Date",
        formatter=Field.format_datetime,
    )
