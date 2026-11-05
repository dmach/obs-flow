from .common import Field, Renderer


class PullRequestRenderer(Renderer):
    id_field = "id"

    id = Field(
        label="ID",
        style={"bold": True},
    )
    title = Field(
        label="Title",
    )
    state = Field(
        label="State",
        style="green",
    )
    is_draft = Field(
        label="Draft",
    )
    latest_revision = Field(
        label="Rev",
    )
