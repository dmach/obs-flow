import json
import logging
import os
import socket
import threading
from pathlib import Path
from django.conf import settings
from django.db import connection
from .policy import evaluate_ref_update, handle_post_receive

logger = logging.getLogger(__name__)

_server_thread = None
_server_running = False
_server_socket = None


def _handle_client(client_sock: socket.socket):
    try:
        data = b""
        while True:
            chunk = client_sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        if not data:
            return

        line = data.decode("utf-8").strip()
        payload = json.loads(line)

        action = payload.get("action")
        username = payload.get("user")
        project_name = payload.get("project")
        package_name = payload.get("package") or None
        updates = payload.get("updates", [])

        if action == "pre-receive":
            response = {"ok": True}
            for upd in updates:
                old_sha = upd.get("old_sha")
                new_sha = upd.get("new_sha")
                ref_name = upd.get("ref")
                allowed, err = evaluate_ref_update(
                    username=username,
                    project_name=project_name,
                    package_name=package_name,
                    old_sha=old_sha,
                    new_sha=new_sha,
                    ref_name=ref_name,
                )
                if not allowed:
                    response = {"ok": False, "error": err}
                    break
        elif action == "post-receive":
            for upd in updates:
                old_sha = upd.get("old_sha")
                new_sha = upd.get("new_sha")
                ref_name = upd.get("ref")
                handle_post_receive(
                    username=username,
                    project_name=project_name,
                    package_name=package_name,
                    old_sha=old_sha,
                    new_sha=new_sha,
                    ref_name=ref_name,
                )
            response = {"ok": True}
        else:
            response = {"ok": False, "error": f"Unknown action '{action}'"}

        client_sock.sendall(json.dumps(response).encode("utf-8") + b"\n")
    except Exception as e:
        logger.exception("Error handling git hook request: %s", e)
        try:
            client_sock.sendall(json.dumps({"ok": False, "error": str(e)}).encode("utf-8") + b"\n")
        except Exception:
            pass
    finally:
        try:
            client_sock.close()
        except Exception:
            pass
        connection.close()


def _serve(sock_path: Path):
    global _server_running, _server_socket
    while _server_running:
        try:
            client, _ = _server_socket.accept()
            t = threading.Thread(target=_handle_client, args=(client,), daemon=True)
            t.start()
        except Exception:
            break


def start_hook_server(socket_path: Path | None = None) -> Path:
    global _server_thread, _server_running, _server_socket
    if _server_running:
        return Path(settings.GIT_HOOKS_SOCKET_PATH)

    sock_path = Path(socket_path or settings.GIT_HOOKS_SOCKET_PATH)
    sock_path.parent.mkdir(parents=True, exist_ok=True)

    if sock_path.exists():
        try:
            sock_path.unlink()
        except OSError:
            pass

    _server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    _server_socket.bind(str(sock_path))
    _server_socket.listen(128)
    _server_running = True

    _server_thread = threading.Thread(target=_serve, args=(sock_path,), daemon=True)
    _server_thread.start()
    logger.info("Started git hooks Unix socket server at %s", sock_path)
    return sock_path


def stop_hook_server():
    global _server_running, _server_socket
    _server_running = False
    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass
        _server_socket = None

    sock_path = getattr(settings, "GIT_HOOKS_SOCKET_PATH", None)
    if sock_path and Path(sock_path).exists():
        try:
            Path(sock_path).unlink()
        except OSError:
            pass
