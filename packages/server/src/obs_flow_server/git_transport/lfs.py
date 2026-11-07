import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from django.conf import settings
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .auth import authenticate_git_user, unauthorized_response
from .views import _resolve_repo

OID_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")
LFS_CONTENT_TYPE = "application/vnd.git-lfs+json"


def get_lfs_root() -> Path:
    return getattr(settings, "GIT_LFS_ROOT", settings.GIT_FORGE_ROOT / "lfs")


def get_lfs_path(oid: str) -> Path:
    clean_oid = oid.lower().strip()
    return get_lfs_root() / clean_oid[0:2] / clean_oid[2:4] / clean_oid


def lfs_response(data: dict, status: int = 200) -> HttpResponse:
    return HttpResponse(
        json.dumps(data),
        content_type=LFS_CONTENT_TYPE,
        status=status,
    )


@csrf_exempt
def lfs_batch_handler(
    request: HttpRequest, project_param: str, package_param: str | None = None
) -> HttpResponse:
    """Handle Git LFS v1 Batch API requests."""
    _project, _pkg, _repo_path = _resolve_repo(project_param, package_param)

    if request.method != "POST":
        return HttpResponseBadRequest("Only POST method is supported for LFS batch API.\n")

    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body.\n")

    operation = payload.get("operation")
    objects = payload.get("objects", [])

    if operation not in ("upload", "download"):
        return HttpResponseBadRequest(f"Unsupported operation '{operation}'.\n")

    # Uploads require authentication
    if operation == "upload":
        user = authenticate_git_user(request)
        if not user:
            return unauthorized_response()

    res_objects = []
    for obj in objects:
        oid = obj.get("oid", "")
        size = obj.get("size", 0)

        if not OID_REGEX.match(oid):
            res_objects.append(
                {
                    "oid": oid,
                    "size": size,
                    "error": {"code": 422, "message": "Invalid OID format"},
                }
            )
            continue

        obj_path = get_lfs_path(oid)

        if operation == "upload":
            if obj_path.exists() and obj_path.stat().st_size == size:
                # Already present on server; no actions required
                res_objects.append(
                    {
                        "oid": oid,
                        "size": size,
                        "authenticated": True,
                    }
                )
            else:
                if package_param:
                    url_name = "git_package_lfs_object"
                    href = reverse(
                        url_name,
                        kwargs={
                            "project": project_param,
                            "package": package_param,
                            "oid": oid,
                        },
                    )
                else:
                    url_name = "git_project_lfs_object"
                    href = reverse(
                        url_name,
                        kwargs={"project": project_param, "oid": oid},
                    )

                res_objects.append(
                    {
                        "oid": oid,
                        "size": size,
                        "authenticated": True,
                        "actions": {
                            "upload": {
                                "href": request.build_absolute_uri(href),
                                "expires_in": 86400,
                            }
                        },
                    }
                )

        elif operation == "download":
            if obj_path.exists():
                if package_param:
                    url_name = "git_package_lfs_object"
                    href = reverse(
                        url_name,
                        kwargs={
                            "project": project_param,
                            "package": package_param,
                            "oid": oid,
                        },
                    )
                else:
                    url_name = "git_project_lfs_object"
                    href = reverse(
                        url_name,
                        kwargs={"project": project_param, "oid": oid},
                    )

                res_objects.append(
                    {
                        "oid": oid,
                        "size": obj_path.stat().st_size,
                        "authenticated": True,
                        "actions": {
                            "download": {
                                "href": request.build_absolute_uri(href),
                                "expires_in": 86400,
                            }
                        },
                    }
                )
            else:
                res_objects.append(
                    {
                        "oid": oid,
                        "size": size,
                        "error": {
                            "code": 404,
                            "message": "Object does not exist",
                        },
                    }
                )

    return lfs_response({"transfer": "basic", "objects": res_objects})


@csrf_exempt
def lfs_object_handler(
    request: HttpRequest,
    project_param: str,
    package_param: str | None,
    oid: str,
) -> HttpResponse:
    """Handle Git LFS object upload (PUT) and download (GET)."""
    _project, _pkg, _repo_path = _resolve_repo(project_param, package_param)

    if not OID_REGEX.match(oid):
        return HttpResponseBadRequest("Invalid OID format.\n")

    dest_path = get_lfs_path(oid)

    if request.method == "PUT":
        user = authenticate_git_user(request)
        if not user:
            return unauthorized_response()

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        hasher = hashlib.sha256()
        with tempfile.NamedTemporaryFile(
            dir=str(dest_path.parent), delete=False
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            try:
                # Stream request body in chunks
                for chunk in request:
                    hasher.update(chunk)
                    tmp_file.write(chunk)
                tmp_file.flush()
            except Exception as e:
                tmp_path.unlink(missing_ok=True)
                return HttpResponseBadRequest(f"Upload failed: {e}\n")

        computed_oid = hasher.hexdigest().lower()
        if computed_oid != oid.lower():
            tmp_path.unlink(missing_ok=True)
            return HttpResponseBadRequest(
                f"SHA256 mismatch: expected '{oid}', computed '{computed_oid}'.\n"
            )

        tmp_path.replace(dest_path)
        return lfs_response({}, status=200)

    elif request.method == "GET":
        if not dest_path.exists():
            raise Http404("LFS object not found.\n")

        return FileResponse(
            open(dest_path, "rb"),
            content_type="application/octet-stream",
            as_attachment=True,
            filename=oid,
        )

    return HttpResponseBadRequest(f"Method '{request.method}' not allowed.\n")


@csrf_exempt
def lfs_verify_handler(
    request: HttpRequest, project_param: str, package_param: str | None = None
) -> HttpResponse:
    """Handle Git LFS verify endpoint (POST)."""
    _project, _pkg, _repo_path = _resolve_repo(project_param, package_param)

    user = authenticate_git_user(request)
    if not user:
        return unauthorized_response()

    try:
        payload = json.loads(request.body)
        oid = payload.get("oid", "")
        size = payload.get("size", -1)
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body.\n")

    if not OID_REGEX.match(oid):
        return HttpResponseBadRequest("Invalid OID format.\n")

    obj_path = get_lfs_path(oid)
    if not obj_path.exists() or obj_path.stat().st_size != size:
        return lfs_response(
            {"message": "Object not found or size mismatch"}, status=404
        )

    return lfs_response({}, status=200)
