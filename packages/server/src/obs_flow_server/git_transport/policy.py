import os
import subprocess
from pathlib import Path
from accounts.models import User
from core.models import Project
from core.git_forge import get_repo_path


def is_git_ancestor(repo_path: Path, old_sha: str, new_sha: str, env: dict[str, str | None] | None = None) -> bool:
    try:
        run_env = os.environ.copy()
        if env:
            for k, v in env.items():
                if v is not None:
                    run_env[k] = v
        res = subprocess.run(
            ["git", "merge-base", "--is-ancestor", old_sha, new_sha],
            cwd=str(repo_path),
            capture_output=True,
            env=run_env,
        )
        return res.returncode == 0
    except Exception:
        return False


def evaluate_ref_update(
    username: str,
    project_name: str,
    package_name: str | None,
    old_sha: str,
    new_sha: str,
    ref_name: str,
    env: dict[str, str | None] | None = None,
) -> tuple[bool, str | None]:
    if not username:
        return False, "Authentication required."

    try:
        user = User.objects.get(username__iexact=username)
        if not user.is_active:
            return False, f"User '{username}' is inactive."
    except User.DoesNotExist:
        return False, f"User '{username}' does not exist."

    try:
        project = Project.objects.select_related("org").get(name=project_name)
    except Project.DoesNotExist:
        return False, f"Project '{project_name}' does not exist."

    is_deletion = set(new_sha) == {"0"}
    is_creation = set(old_sha) == {"0"}

    # Project branch: refs/heads/{project.branch_name}
    project_branch_ref = f"refs/heads/{project.branch_name}"

    if ref_name == project_branch_ref:
        if is_deletion:
            return False, f"Deletion of project branch '{project.branch_name}' is not allowed."

        if project.workflow_type == Project.WorkflowType.STAGING:
            return (
                False,
                f"Direct push to branch '{project.branch_name}' is not allowed for staging workflow. "
                f"Changes must be submitted via pull request.",
            )

        # Direct workflow: check force-push if not creation
        if not is_creation and not is_deletion:
            repo_path = get_repo_path(project.org.name, package_name)
            if repo_path.exists() and not is_git_ancestor(repo_path, old_sha, new_sha, env):
                return False, f"Force-push to project branch '{project.branch_name}' is not allowed."

        return True, None

    # Private user branches: refs/heads/private/<username>/...
    private_prefix = f"refs/heads/private/{user.username}/"
    if ref_name.startswith(private_prefix):
        return True, None

    if ref_name.startswith("refs/heads/private/"):
        return False, f"Cannot push to private branch of another user. Only '{private_prefix}*' is permitted."

    # All other refs are rejected
    return (
        False,
        f"Ref '{ref_name}' is not allowed. Only project branch '{project_branch_ref}' "
        f"or 'refs/heads/private/{user.username}/...' are permitted.",
    )


def handle_post_receive(
    username: str,
    project_name: str,
    package_name: str | None,
    old_sha: str,
    new_sha: str,
    ref_name: str,
) -> None:
    # Hook for post-receive push notifications
    pass
