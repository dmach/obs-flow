import msgspec


class CommentDTO(msgspec.Struct):
    id: int
    target_type: str
    target_id: str
    author: str
    body: str
    created_at: str
    updated_at: str
    path: str | None = None
    line_number: int | None = None


class CommentAddRequest(msgspec.Struct):
    target_type: str
    target_id: str
    author: str
    body: str
    path: str | None = None
    line_number: int | None = None


class CommentAddResponse(msgspec.Struct):
    comment: CommentDTO


class CommentListRequest(msgspec.Struct):
    target_type: str
    target_id: str


class CommentListResponse(msgspec.Struct):
    comments: list[CommentDTO]
