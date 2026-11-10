import subprocess
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from accounts.models import User
from core.git_forge import get_repo_path
from core.models import Package, Project, validate_entity_name, validate_org_name
from pull_requests.fingerprint import PRRevisionPayload
from pull_requests.models import PullRequest, PullRequestRevision

ZERO_SHA = "0" * 40


def _rev_parse_branch(repo_path, branch: str) -> str:
    """Resolve refs/heads/<branch> in a bare repo; return "" if unresolvable."""
    if not repo_path.exists():
        return ""
    p = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"refs/heads/{branch}"],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
    )
    return p.stdout.strip() if p.returncode == 0 else ""


def _next_number(project: Project, package: Package | None) -> int:
    # Serialize number assignment per project (no-op on SQLite).
    list(Project.objects.select_for_update().filter(pk=project.pk))
    max_num = PullRequest.objects.filter(project=project, package=package).aggregate(Max("number"))["number__max"]
    return (max_num or 0) + 1


def create_pull_request(
    *,
    author: User,
    target_project: Project,
    target_package: Package | None,
    title: str,
    source_owner: str,
    source_repo: str,
    source_branch: str,
    is_draft: bool = False,
    head_sha: str = "",
    base_sha: str = "",
) -> PullRequest:
    """Create a PR with its first revision. Raises ValueError on invalid input."""
    from pull_requests.api import provision_reviews_for_revision
    from django.core.exceptions import ValidationError

    try:
        validate_org_name(source_owner)
        validate_entity_name(source_repo)
    except ValidationError as e:
        raise ValueError("; ".join(e.messages))

    # Retry once: concurrent creators can pick the same number; the unique constraint rejects the loser.
    for attempt in (1, 2):
        try:
            with transaction.atomic():
                pr = PullRequest.objects.create(
                    project=target_project,
                    package=target_package,
                    number=_next_number(target_project, target_package),
                    author=author,
                    title=title,
                    source_owner=source_owner,
                    source_repo=source_repo,
                    source_branch=source_branch,
                    state=PullRequest.State.OPEN,
                )
            break
        except IntegrityError:
            if attempt == 2:
                raise ValueError("Could not allocate a pull request number; retry.")

    timeout_minutes = target_project.effective_review_debounce_minutes
    if is_draft:
        rev_is_draft = True
        rev_draft_expires_at = None
    elif timeout_minutes == 0:
        rev_is_draft = False
        rev_draft_expires_at = None
    else:
        rev_is_draft = True
        rev_draft_expires_at = timezone.now() + timedelta(minutes=timeout_minutes)

    target_branch = target_project.branch_name or "main"
    if not head_sha or not base_sha:
        target_repo = get_repo_path(
            target_project.org.name if target_project.org else "",
            target_package.name if target_package else None,
        )
        source_path = get_repo_path(source_owner, source_repo)
        base_sha = base_sha or _rev_parse_branch(target_repo, target_branch)
        head_sha = head_sha or _rev_parse_branch(source_path, source_branch)

    resolved_head = head_sha or ZERO_SHA
    resolved_base = base_sha or ZERO_SHA
    fingerprint = PRRevisionPayload(
        head_sha=resolved_head,
        base_sha=resolved_base,
        target_branch=target_branch,
    ).compute_fingerprint()

    rev = PullRequestRevision.objects.create(
        pull_request=pr,
        revision_number=1,
        head_sha=resolved_head,
        base_sha=resolved_base,
        fingerprint=fingerprint,
        is_draft=rev_is_draft,
        draft_expires_at=rev_draft_expires_at,
    )

    if not rev.is_draft:
        provision_reviews_for_revision(rev)

    return pr
