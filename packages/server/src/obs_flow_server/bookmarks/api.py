import msgspec
from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Q

from obs_flow_common.messages import (
    BookmarkDTO,
    BookmarkListRequest,
    BookmarkListResponse,
    BookmarkAddRequest,
    BookmarkAddResponse,
    BookmarkRemoveRequest,
    BookmarkRemoveResponse,
    BookmarkImportRequest,
    BookmarkImportResponse,
)
from obs_flow_server.api import api
from bookmarks.models import Bookmark
from bookmarks.helpers import is_safe_url
from accounts.helpers import get_authenticated_user


@api.post("/api/v1/bookmark/list")
async def list_bookmarks(payload: BookmarkListRequest, request):
    def do_list():
        user = get_authenticated_user(request)
        qs = Bookmark.objects.filter(user=user)

        if payload.names or payload.name_contains:
            query = Q()
            if payload.names:
                query |= Q(name__in=payload.names)
            if payload.name_contains:
                for nc in payload.name_contains:
                    query |= Q(name__icontains=nc)
            qs = qs.filter(query)

        dtos = [BookmarkDTO(id=b.id, name=b.name, url=b.url) for b in qs]
        res = BookmarkListResponse(bookmarks=dtos)
        return msgspec.structs.asdict(res)
    return await sync_to_async(do_list)()


@api.post("/api/v1/bookmark/add")
async def add_bookmark(payload: BookmarkAddRequest, request):
    def do_add():
        user = get_authenticated_user(request)
        name = payload.name.strip()
        url = payload.url.strip()

        if not name:
            raise ValueError("Name cannot be empty")
        if not url:
            raise ValueError("URL cannot be empty")
        if not is_safe_url(url):
            raise ValueError("Invalid URL: must be a relative path starting with '/'")

        with transaction.atomic():
            if Bookmark.objects.filter(user=user, name=name).exists():
                raise ValueError(f"Bookmark with name '{name}' already exists")

            bookmark = Bookmark.objects.create(user=user, name=name, url=url)
            dto = BookmarkDTO(id=bookmark.id, name=bookmark.name, url=bookmark.url)
            res = BookmarkAddResponse(bookmark=dto)
            return msgspec.structs.asdict(res)
    return await sync_to_async(do_add)()


@api.post("/api/v1/bookmark/remove")
async def remove_bookmark(payload: BookmarkRemoveRequest, request):
    def do_remove():
        user = get_authenticated_user(request)
        with transaction.atomic():
            try:
                bookmark = Bookmark.objects.get(user=user, name=payload.name)
                bookmark.delete()
                success = True
            except Bookmark.DoesNotExist:
                success = False

            res = BookmarkRemoveResponse(success=success)
            return msgspec.structs.asdict(res)
    return await sync_to_async(do_remove)()


@api.post("/api/v1/bookmark/import")
async def import_bookmarks(payload: BookmarkImportRequest, request):
    def do_import():
        user = get_authenticated_user(request)
        imported_count = 0
        updated_count = 0

        with transaction.atomic():
            for item in payload.items:
                name = item.name.strip()
                url = item.url.strip()

                if not name:
                    raise ValueError("Name cannot be empty")
                if not url:
                    raise ValueError("URL cannot be empty")
                if not is_safe_url(url):
                    raise ValueError(f"Invalid URL for bookmark '{name}': must be a relative path starting with '/'")

                bookmark = Bookmark.objects.filter(user=user, name=name).first()
                if bookmark:
                    if not payload.force:
                        raise ValueError(f"Conflict: Bookmark with name '{name}' already exists. Use --force to overwrite.")
                    bookmark.url = url
                    bookmark.save()
                    updated_count += 1
                else:
                    Bookmark.objects.create(user=user, name=name, url=url)
                    imported_count += 1

            res = BookmarkImportResponse(imported_count=imported_count, updated_count=updated_count)
            return msgspec.structs.asdict(res)
    return await sync_to_async(do_import)()
