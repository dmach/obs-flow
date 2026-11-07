import os
import shlex
import subprocess
import sys
from pathlib import Path
from django.conf import settings
from accounts.models import User
from git_transport.views import _resolve_repo

ALLOWED_COMMANDS = {
    "git-upload-pack": "upload-pack",
    "git-receive-pack": "receive-pack",
}


def parse_ssh_command(command_str: str) -> tuple[str, str, str | None]:
    """Parse SSH_ORIGINAL_COMMAND into (git_service, project_param, package_param).

    Supports formats like:
      - git-upload-pack 'project/package.git'
      - git-receive-pack 'project.git'
      - git-upload-pack '/project/package'
      - git-upload-pack 'packages/project/package.git'
      - git-upload-pack 'projects/project.git'
    """
    args = shlex.split(command_str)
    if not args:
        raise ValueError("Empty SSH command.")

    cmd = args[0]
    if cmd not in ALLOWED_COMMANDS:
        raise ValueError(
            f"Command '{cmd}' not permitted. Only git-upload-pack and git-receive-pack are allowed."
        )

    if len(args) < 2:
        raise ValueError(f"Missing repository path for command '{cmd}'.")

    raw_path = args[1].strip().strip("'\"").lstrip("/")

    # Normalize path if prefixed by projects/ or packages/
    parts = [p for p in raw_path.split("/") if p]
    if len(parts) >= 3 and parts[0] == "packages":
        project_param = parts[1]
        package_param = parts[2]
    elif len(parts) >= 2 and parts[0] == "projects":
        project_param = parts[1]
        package_param = None
    elif len(parts) == 1:
        project_param = parts[0]
        package_param = None
    elif len(parts) == 2:
        project_param = parts[0]
        package_param = parts[1]
    else:
        raise ValueError(f"Invalid repository path: '{raw_path}'.")

    if project_param:
        project_param = project_param.removesuffix(".git")
    if package_param:
        package_param = package_param.removesuffix(".git")

    return cmd, project_param, package_param


def handle_ssh_command(
    username: str,
    command_str: str,
    stdin=None,
    stdout=None,
    stderr=None,
) -> int:
    """Execute git-upload-pack or git-receive-pack for an SSH session."""
    err_out = stderr or sys.stderr

    try:
        cmd, project_param, package_param = parse_ssh_command(command_str)
    except ValueError as e:
        err_out.write(f"OBS Flow SSH Error: {e}\n")
        return 1

    try:
        user = User.objects.get(username__iexact=username)
        if not user.is_active:
            err_out.write(f"OBS Flow SSH Error: User '{username}' is inactive.\n")
            return 1
    except User.DoesNotExist:
        err_out.write(f"OBS Flow SSH Error: User '{username}' does not exist.\n")
        return 1

    try:
        project, package_name, repo_path = _resolve_repo(project_param, package_param)
    except Exception as e:
        err_out.write(f"OBS Flow SSH Error: {e}\n")
        return 1

    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}
    env["OBS_FLOW_USER"] = user.username
    env["OBS_FLOW_PROJECT"] = project.name
    if package_name:
        env["OBS_FLOW_PACKAGE"] = package_name
    socket_path = getattr(settings, "GIT_HOOKS_SOCKET_PATH", None)
    if socket_path:
        env["OBS_FLOW_HOOKS_SOCKET"] = str(socket_path)

    hooks_path = repo_path / "hooks"

    if cmd == "git-upload-pack":
        exec_args = ["git", "upload-pack", str(repo_path)]
    else:
        exec_args = [
            "git",
            "-c",
            f"core.hooksPath={hooks_path}",
            "receive-pack",
            str(repo_path),
        ]

    try:
        proc = subprocess.Popen(
            exec_args,
            stdin=stdin or sys.stdin,
            stdout=stdout or sys.stdout,
            stderr=err_out,
            env=env,
        )
        return proc.wait()
    except Exception as e:
        err_out.write(f"OBS Flow SSH Error executing {cmd}: {e}\n")
        return 1
