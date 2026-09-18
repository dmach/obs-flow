import msgspec


class BookmarkDTO(msgspec.Struct):
    id: int
    name: str
    url: str


class BookmarkListRequest(msgspec.Struct):
    names: list[str] | None = None
    name_contains: list[str] | None = None


class BookmarkListResponse(msgspec.Struct):
    bookmarks: list[BookmarkDTO]


class BookmarkAddRequest(msgspec.Struct):
    name: str
    url: str


class BookmarkAddResponse(msgspec.Struct):
    bookmark: BookmarkDTO


class BookmarkRemoveRequest(msgspec.Struct):
    name: str


class BookmarkRemoveResponse(msgspec.Struct):
    success: bool


class BookmarkImportRequest(msgspec.Struct):
    items: list[BookmarkAddRequest]
    force: bool = False


class BookmarkImportResponse(msgspec.Struct):
    imported_count: int
    updated_count: int
