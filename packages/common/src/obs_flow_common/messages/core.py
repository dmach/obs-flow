import msgspec


class ReviewDetail(msgspec.Struct):
    """Details of an individual review."""
    reviewer: str
    state: str
    actor: str | None = None
    when: str | None = None
    why: str | None = None
