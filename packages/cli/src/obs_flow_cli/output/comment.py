from .common import Field, Renderer


class CommentRenderer(Renderer):
    id_field = "id"

    id = Field(
        label="ID",
        style={"bold": True},
    )
    author = Field(
        label="Author",
        style="cyan",
    )
    target_type = Field(
        label="Target Type",
    )
    target_id = Field(
        label="Target ID",
    )
    created_at = Field(
        label="Created At",
    )
    body = Field(
        label="Comment",
    )
