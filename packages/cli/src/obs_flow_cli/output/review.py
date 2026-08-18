from .common import Field, Renderer
from .formatters import format_reviewer_dto, format_user_dto


class ReviewRenderer(Renderer):
    reviewer = Field(
        label="Reviewer",
        style={"bold": True},
        formatter=format_reviewer_dto,
    )
    state = Field(
        label="State",
        style=lambda v: {
            "accepted": "green",
            "rejected": "red",
        }.get(v),
        formatter=lambda v: v.upper(),
    )
    actor = Field(
        label="Actor",
        formatter=format_user_dto,
        skip=Field.skip_none,
    )
    when = Field(
        label="Date",
        formatter=Field.format_datetime,
        skip=Field.skip_none,
    )
    why = Field(
        label="Reason",
        skip=Field.skip_none,
    )
