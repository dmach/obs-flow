from .common import Field, Renderer


class PackageRenderer(Renderer):
    id_field = "name"

    id = Field(
        label="ID",
        style={"bold": True},
    )
    project = Field(
        label="Project",
    )
    name = Field(
        label="Name",
    )
    forked_from = Field(
        label="Forked From",
        style="cyan",
    )
