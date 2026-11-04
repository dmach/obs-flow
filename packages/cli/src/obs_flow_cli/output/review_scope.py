from .common import Field, Renderer


class ReviewScopeRenderer(Renderer):
    id_field = "name"

    name = Field(
        label="Name",
        style={"bold": True},
    )
    include_globs = Field(
        label="Include",
        formatter=lambda v: ", ".join(v),
    )
    exclude_globs = Field(
        label="Exclude",
        formatter=lambda v: ", ".join(v),
        skip=Field.skip_empty,
    )
