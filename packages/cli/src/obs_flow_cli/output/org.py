from .common import Field, Renderer


class OrgRenderer(Renderer):
    id_field = "name"

    id = Field(
        label="ID",
        style={"bold": True},
    )
    name = Field(
        label="Name",
    )
    is_personal = Field(
        label="Personal",
        style="cyan",
    )
    user = Field(
        label="User",
    )
