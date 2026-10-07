from .common import Field, Renderer


class ProjectRenderer(Renderer):
    id = Field(
        label="ID",
        style={"bold": True},
    )
    name = Field(
        label="Name",
    )
    workflow_type = Field(
        label="Workflow Type",
        style="cyan",
    )
