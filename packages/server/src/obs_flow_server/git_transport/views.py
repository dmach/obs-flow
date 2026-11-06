import os
import subprocess
from pathlib import Path
from django.conf import settings
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseServerError,
)
from django.views.decorators.csrf import csrf_exempt

from core.models import Package, Project
from core.git_forge import ensure_git_repo
from .auth import authenticate_git_user, unauthorized_response


def _pkt_line(data: bytes) -> bytes:
    return f"{len(data) + 4:04x}".encode("ascii") + data


def _resolve_repo(project_param: str, package_param: str | None = None) -> tuple[Project, str | None, Path]:
    project_name = project_param.removesuffix(".git")
    try:
        project = Project.objects.select_related("org").get(name=project_name)
    except Project.DoesNotExist:
        raise Http404(f"Project '{project_name}' not found")

    package_name = None
    if package_param:
        package_name = package_param.removesuffix(".git")
        if not Package.objects.filter(project=project, name=package_name).exists():
            raise Http404(f"Package '{package_name}' not found in project '{project_name}'")

    repo_path = ensure_git_repo(
        org_name=project.org.name,
        package_name=package_name,
        initial_branch=project.branch_name,
    )
    return project, package_name, repo_path


def _info_refs_handler(request: HttpRequest, project_param: str, package_param: str | None = None) -> HttpResponse:
    user = authenticate_git_user(request)
    service = request.GET.get("service")
    if service not in ("git-upload-pack", "git-receive-pack"):
        return HttpResponseBadRequest("Only Smart HTTP is supported (missing or invalid service parameter).\n")

    # Push requires authentication; clone/fetch allows anonymous access
    if service == "git-receive-pack" and not user:
        return unauthorized_response()

    _project, _pkg_name, repo_path = _resolve_repo(project_param, package_param)

    git_cmd = service.replace("git-", "")
    try:
        proc = subprocess.run(
            ["git", git_cmd, "--stateless-rpc", "--advertise-refs", str(repo_path)],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        return HttpResponseServerError(f"Git execution failed: {e.stderr.decode('utf-8', errors='replace')}\n")

    body = _pkt_line(f"# service={service}\n".encode("ascii")) + b"0000" + proc.stdout
    response = HttpResponse(body, content_type=f"application/x-{service}-advertisement")
    response["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def _upload_pack_handler(request: HttpRequest, project_param: str, package_param: str | None = None) -> HttpResponse:
    _project, _pkg_name, repo_path = _resolve_repo(project_param, package_param)

    try:
        proc = subprocess.Popen(
            ["git", "upload-pack", "--stateless-rpc", str(repo_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_data, stderr_data = proc.communicate(input=request.body)
        if proc.returncode != 0:
            return HttpResponseServerError(
                f"git-upload-pack failed: {stderr_data.decode('utf-8', errors='replace')}\n"
            )
    except Exception as e:
        return HttpResponseServerError(f"Error running git-upload-pack: {e}\n")

    response = HttpResponse(stdout_data, content_type="application/x-git-upload-pack-result")
    response["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


def _receive_pack_handler(request: HttpRequest, project_param: str, package_param: str | None = None) -> HttpResponse:
    user = authenticate_git_user(request)
    if not user:
        return unauthorized_response()

    project, package_name, repo_path = _resolve_repo(project_param, package_param)

    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}
    env["OBS_FLOW_USER"] = user.username
    env["OBS_FLOW_PROJECT"] = project.name
    if package_name:
        env["OBS_FLOW_PACKAGE"] = package_name
    socket_path = getattr(settings, "GIT_HOOKS_SOCKET_PATH", None)
    if socket_path:
        env["OBS_FLOW_HOOKS_SOCKET"] = str(socket_path)

    hooks_path = repo_path / "hooks"
    try:
        proc = subprocess.Popen(
            ["git", "-c", f"core.hooksPath={hooks_path}", "receive-pack", "--stateless-rpc", str(repo_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        stdout_data, stderr_data = proc.communicate(input=request.body)
        if proc.returncode != 0:
            # Note: git receive-pack might exit non-zero on hook rejection,
            # but its stdout contains the pack protocol rejection messages.
            # Return stdout if available so git client gets the hook rejection.
            if stdout_data:
                response = HttpResponse(stdout_data, content_type="application/x-git-receive-pack-result")
                response["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
                response["Pragma"] = "no-cache"
                return response
            return HttpResponseServerError(
                f"git-receive-pack failed: {stderr_data.decode('utf-8', errors='replace')}\n"
            )
    except Exception as e:
        return HttpResponseServerError(f"Error running git-receive-pack: {e}\n")

    response = HttpResponse(stdout_data, content_type="application/x-git-receive-pack-result")
    response["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


# --- Package-level views ---
def package_repo_root(request: HttpRequest, project: str, package: str) -> HttpResponse:
    _project, _pkg_name, _repo_path = _resolve_repo(project, package)
    return HttpResponse("Git repository\n", content_type="text/plain")


def package_info_refs(request: HttpRequest, project: str, package: str) -> HttpResponse:
    return _info_refs_handler(request, project, package)


@csrf_exempt
def package_upload_pack(request: HttpRequest, project: str, package: str) -> HttpResponse:
    return _upload_pack_handler(request, project, package)


@csrf_exempt
def package_receive_pack(request: HttpRequest, project: str, package: str) -> HttpResponse:
    return _receive_pack_handler(request, project, package)


# --- Project-level views ---
def project_repo_root(request: HttpRequest, project: str) -> HttpResponse:
    _project, _pkg_name, _repo_path = _resolve_repo(project, None)
    return HttpResponse("Git repository\n", content_type="text/plain")


def project_info_refs(request: HttpRequest, project: str) -> HttpResponse:
    return _info_refs_handler(request, project, None)


@csrf_exempt
def project_upload_pack(request: HttpRequest, project: str) -> HttpResponse:
    return _upload_pack_handler(request, project, None)


@csrf_exempt
def project_receive_pack(request: HttpRequest, project: str) -> HttpResponse:
    return _receive_pack_handler(request, project, None)
