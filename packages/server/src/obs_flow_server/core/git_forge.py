import subprocess
from pathlib import Path
from django.conf import settings


HOOK_SCRIPT = """#!/usr/bin/env python3
import sys
import os
import socket
import json

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else os.path.basename(sys.argv[0])
    socket_path = os.environ.get("OBS_FLOW_HOOKS_SOCKET")
    if not socket_path or not os.path.exists(socket_path):
        return

    user = os.environ.get("OBS_FLOW_USER", "")
    project = os.environ.get("OBS_FLOW_PROJECT", "")
    package = os.environ.get("OBS_FLOW_PACKAGE", "")

    updates = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) == 3:
            updates.append({"old_sha": parts[0], "new_sha": parts[1], "ref": parts[2]})

    if not updates:
        return

    payload = {
        "action": action,
        "user": user,
        "project": project,
        "package": package,
        "updates": updates,
    }

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(socket_path)
        s.sendall(json.dumps(payload).encode("utf-8") + b"\\n")
        resp_data = s.makefile().readline()
        s.close()
        resp = json.loads(resp_data)
        if not resp.get("ok", True):
            sys.stderr.write(f"\\n[OBS Flow] Push rejected: {resp.get('error', 'Unauthorized')}\\n\\n")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"\\n[OBS Flow] Authorization check failed: {e}\\n\\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""


def install_git_hooks(repo_path: Path):
    hooks_dir = repo_path / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for hook_name in ("pre-receive", "post-receive"):
        hook_path = hooks_dir / hook_name
        hook_path.write_text(HOOK_SCRIPT)
        try:
            hook_path.chmod(0o755)
        except OSError:
            pass


def get_repo_path(org_name: str, package_name: str | None = None) -> Path:
    repo_name = f"{package_name}.git" if package_name else "_project.git"
    return settings.GIT_FORGE_ROOT / org_name / repo_name


def ensure_git_repo(org_name: str, package_name: str | None = None, initial_branch: str | None = None) -> Path:
    repo_path = get_repo_path(org_name, package_name)
    if not repo_path.exists():
        repo_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "--bare", str(repo_path)], check=True, capture_output=True)
        if initial_branch:
            subprocess.run(
                ["git", "symbolic-ref", "HEAD", f"refs/heads/{initial_branch}"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
    install_git_hooks(repo_path)
    return repo_path


def fork_git_repo(
    source_org: str,
    source_package: str,
    target_org: str,
    target_package: str,
    branch: str | None = None,
) -> Path:
    source_path = get_repo_path(source_org, source_package)
    target_path = get_repo_path(target_org, target_package)
    if not target_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.exists():
            subprocess.run(
                ["git", "clone", "--bare", str(source_path), str(target_path)],
                check=True,
                capture_output=True,
            )
            if branch:
                subprocess.run(
                    ["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"],
                    cwd=str(target_path),
                    check=True,
                    capture_output=True,
                )
        else:
            ensure_git_repo(target_org, target_package, initial_branch=branch)
    return target_path
