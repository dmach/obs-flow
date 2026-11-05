from .common import Field, Renderer


class ProjectRenderer(Renderer):
    id_field = "name"

    id = Field(
        label="ID",
        style={"bold": True},
    )
    name = Field(
        label="Name",
    )
    org = Field(
        label="Org",
    )
    branch_name = Field(
        label="Branch",
    )
    workflow_type = Field(
        label="Workflow Type",
        style="cyan",
    )
