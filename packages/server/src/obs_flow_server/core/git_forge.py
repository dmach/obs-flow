import subprocess
from pathlib import Path
from django.conf import settings


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
