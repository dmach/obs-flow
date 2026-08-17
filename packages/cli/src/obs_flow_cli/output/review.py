from .common import Field, Renderer


class ReviewRenderer(Renderer):
    reviewer = Field(
        label="Reviewer",
        style={"bold": True},
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
