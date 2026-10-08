from .common import Field, Renderer


class BookmarkRenderer(Renderer):
    id_field = "name"

    id = Field(
        label="ID",
        style={"bold": True},
    )
    name = Field(
        label="Name",
        style="green",
    )
    url = Field(
        label="URL",
    )
