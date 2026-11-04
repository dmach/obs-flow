from .common import Field, Renderer
from .formatters import format_reviewer_dto, format_user_dto, get_reviewer_id


class ReviewRenderer(Renderer):
    id_field = lambda item: f"{get_reviewer_id(item.reviewer)} ({item.state.upper()}{' [inherited]' if getattr(item, 'is_inherited', False) else ''})"

    reviewer = Field(
        label="Reviewer",
        style={"bold": True},
        formatter=format_reviewer_dto,
    )
    scope = Field(
        label="Scope",
        skip=Field.skip_none,
    )
    state = Field(
        label="State",
        style=lambda v: {
            "accepted": "green",
            "rejected": "red",
            "skipped": "yellow",
        }.get(v),
        formatter=lambda v: v.upper(),
    )
    is_inherited = Field(
        label="Inherited",
        formatter=Field.format_yes_no,
        skip=lambda v: not v,
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
