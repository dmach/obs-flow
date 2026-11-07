import re
import subprocess
from pathlib import Path
from typing import TypedDict, Literal


class DiffLine(TypedDict):
    type: Literal["add", "del", "context", "hunk"]
    old_no: int | None
    new_no: int | None
    text: str


class FileDiff(TypedDict):
    path: str
    old_path: str
    status: Literal["added", "modified", "deleted", "renamed"]
    additions: int
    deletions: int
    is_binary: bool
    lines: list[DiffLine]


class GitCommit(TypedDict):
    sha: str
    short_sha: str
    author_name: str
    author_email: str
    date: str
    title: str


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


def get_git_commits(repo_path: Path, ref: str = "HEAD", limit: int = 50) -> list[GitCommit]:
    if not repo_path.exists():
        return []
    try:
        proc = subprocess.run(
            [
                "git",
                "log",
                f"-n{limit}",
                "--format=%H%x00%h%x00%an%x00%ae%x00%cd%x00%s",
                "--date=format:%Y-%m-%d %H:%M:%S",
                ref,
            ],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return []

    commits: list[GitCommit] = []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) == 6:
            full_sha, short_sha, author_name, author_email, date_str, title = parts
            commits.append({
                "sha": full_sha,
                "short_sha": short_sha,
                "author_name": author_name,
                "author_email": author_email,
                "date": date_str,
                "title": title,
            })
    return commits


def parse_git_diff(raw_diff: str) -> list[FileDiff]:
    file_diffs: list[FileDiff] = []
    if not raw_diff.strip():
        return file_diffs

    raw_files = raw_diff.split("\ndiff --git ")
    for idx, raw_file in enumerate(raw_files):
        if idx == 0 and raw_file.startswith("diff --git "):
            raw_file = raw_file[len("diff --git ") :]
        lines = raw_file.splitlines()
        if not lines:
            continue

        header_parts = lines[0].split(" ", 1)
        raw_old = header_parts[0] if len(header_parts) > 0 else ""
        raw_new = header_parts[1] if len(header_parts) > 1 else raw_old
        old_path = raw_old[2:] if raw_old.startswith("a/") else raw_old
        new_path = raw_new[2:] if raw_new.startswith("b/") else raw_new

        status: Literal["added", "modified", "deleted", "renamed"] = "modified"
        if "new file mode" in raw_file:
            status = "added"
        elif "deleted file mode" in raw_file:
            status = "deleted"
        elif "similarity index" in raw_file or "rename from" in raw_file:
            status = "renamed"

        is_binary = "Binary files " in raw_file and " differ" in raw_file

        hunk_lines: list[DiffLine] = []
        additions = 0
        deletions = 0
        old_no = 0
        new_no = 0
        in_hunks = False

        for line in lines[1:]:
            if line.startswith("@@"):
                in_hunks = True
                m = re.match(r"^@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@(.*)", line)
                if m:
                    old_no = int(m.group(1))
                    new_no = int(m.group(2))
                hunk_lines.append({
                    "type": "hunk",
                    "old_no": None,
                    "new_no": None,
                    "text": line,
                })
            elif in_hunks:
                if line.startswith("+"):
                    additions += 1
                    hunk_lines.append({
                        "type": "add",
                        "old_no": None,
                        "new_no": new_no,
                        "text": line[1:],
                    })
                    new_no += 1
                elif line.startswith("-"):
                    deletions += 1
                    hunk_lines.append({
                        "type": "del",
                        "old_no": old_no,
                        "new_no": None,
                        "text": line[1:],
                    })
                    old_no += 1
                elif line.startswith(" "):
                    hunk_lines.append({
                        "type": "context",
                        "old_no": old_no,
                        "new_no": new_no,
                        "text": line[1:],
                    })
                    old_no += 1
                    new_no += 1

        file_diffs.append({
            "path": new_path if status != "deleted" else old_path,
            "old_path": old_path,
            "status": status,
            "additions": additions,
            "deletions": deletions,
            "is_binary": is_binary,
            "lines": hunk_lines,
        })
    return file_diffs


def get_git_diff(repo_path: Path, base_ref: str, head_ref: str) -> list[FileDiff]:
    if not repo_path.exists():
        return []
    try:
        proc = subprocess.run(
            ["git", "diff", "-M", f"{base_ref}...{head_ref}"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_git_diff(proc.stdout)
    except subprocess.CalledProcessError:
        return []


def ensure_pr_git_refs(pr) -> tuple[Path, str, str]:
    from core.git_forge import get_repo_path, ensure_git_repo

    target_repo = ensure_git_repo(
        pr.target_owner,
        pr.target_repo if pr.package else None,
        initial_branch=pr.target_branch,
    )
    source_repo = get_repo_path(pr.source_owner, pr.source_repo if pr.package else None)

    target_ref = pr.target_branch
    source_ref = pr.source_branch

    try:
        if target_repo.resolve() == source_repo.resolve():
            return target_repo, target_ref, source_ref
    except Exception:
        pass

    if target_repo.exists() and source_repo.exists():
        pull_ref = f"refs/pull/{pr.number}/head"
        subprocess.run(
            ["git", "fetch", str(source_repo), f"{pr.source_branch}:{pull_ref}"],
            cwd=str(target_repo),
            capture_output=True,
            check=False,
        )
        return target_repo, target_ref, pull_ref

    return target_repo, target_ref, source_ref


