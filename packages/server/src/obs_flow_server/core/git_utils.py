import subprocess
from pathlib import Path
from typing import TypedDict, Literal


class GitTreeEntry(TypedDict):
    mode: str
    type: Literal["blob", "tree", "commit"]
    sha: str
    size: int | None
    name: str
    commit_msg: str | None
    commit_date: str | None


def get_git_tree(repo_path: Path, ref: str, path: str = "") -> list[GitTreeEntry]:
    if not repo_path.exists():
        return []
    target = f"{ref}:{path}" if path else ref
    try:
        proc = subprocess.run(
            ["git", "ls-tree", "-l", target],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return []

    entries = []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        parts = line.split(maxsplit=4)
        if len(parts) == 5:
            mode, obj_type, sha, size_str, name = parts
            size = int(size_str) if size_str.strip() != "-" else None
            name = name.strip()
            
            # Fetch last commit info
            entry_path = f"{path}/{name}" if path else name
            commit_msg = None
            commit_date = None
            try:
                log_proc = subprocess.run(
                    ["git", "log", "-1", "--format=%s%x00%cd", "--date=format:%Y-%m-%d %H:%M:%S", ref, "--", entry_path],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if log_proc.stdout:
                    msg, date = log_proc.stdout.strip().split('\x00', 1)
                    commit_msg = msg
                    commit_date = date
            except Exception:
                pass

            entries.append({
                "mode": mode,
                "type": obj_type,  # type: ignore
                "sha": sha,
                "size": size,
                "name": name,
                "commit_msg": commit_msg,
                "commit_date": commit_date,
            })
    
    entries.sort(key=lambda e: (0 if e["type"] == "tree" else 1, e["name"]))
    return entries


def get_git_blob(repo_path: Path, ref: str, path: str) -> str | bytes | None:
    if not repo_path.exists():
        return None
    target = f"{ref}:{path}"
    try:
        proc = subprocess.run(
            ["git", "show", target],
            cwd=str(repo_path),
            capture_output=True,
            check=True,
        )
        try:
            return proc.stdout.decode("utf-8")
        except UnicodeDecodeError:
            return proc.stdout
    except subprocess.CalledProcessError:
        return None


def get_git_type(repo_path: Path, ref: str, path: str) -> Literal["blob", "tree", "commit"] | None:
    if not repo_path.exists():
        return None if path else "tree"
    if not path:
        return "tree"
    try:
        proc = subprocess.run(
            ["git", "ls-tree", ref, path],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
        line = proc.stdout.strip()
        if not line:
            return None
        parts = line.split(maxsplit=3)
        if len(parts) >= 2:
            return parts[1]  # type: ignore
    except subprocess.CalledProcessError:
        pass
    return None
