"""Record a new revision for a native PR from the current heads of its repos.

Run through `manage.py shell < scripts/add_pr_revision.py` with PR_PROJECT, PR_PACKAGE
(optional) and PR_NUMBER in the environment. Mirrors the revision logic of
/api/v1/pr/create (there is no API that adds a revision to a native PR).
"""

import os
import subprocess
from datetime import timedelta

from django.utils import timezone

from core.git_forge import get_repo_path
from pull_requests.api import provision_reviews_for_revision
from pull_requests.fingerprint import PRRevisionPayload
from pull_requests.models import PullRequest, PullRequestRevision


def rev_parse(owner, repo, ref):
    path = get_repo_path(owner, repo)
    return subprocess.run(["git", "rev-parse", ref], cwd=str(path), capture_output=True, text=True, check=True).stdout.strip()


package = os.environ.get("PR_PACKAGE") or None
pr = PullRequest.objects.get(project__name=os.environ["PR_PROJECT"], package__name=package, number=int(os.environ["PR_NUMBER"]))
project = pr.target_project
target_branch = pr.target_branch or "main"
head_sha = rev_parse(pr.source_owner, pr.source_repo, pr.source_branch)
base_sha = rev_parse(project.org.name if project.org else "", pr.package.name if pr.package else None, target_branch)
fingerprint = PRRevisionPayload(head_sha=head_sha, base_sha=base_sha, target_branch=target_branch).compute_fingerprint()

latest = pr.revisions.order_by("-revision_number").first()
if latest and latest.fingerprint == fingerprint:
    print(f"{pr.formatted_id}: head unchanged, no new revision")
else:
    timeout_minutes = project.effective_review_debounce_minutes
    draft = timeout_minutes != 0
    rev = PullRequestRevision.objects.create(
        pull_request=pr,
        revision_number=(latest.revision_number + 1) if latest else 1,
        head_sha=head_sha,
        base_sha=base_sha,
        fingerprint=fingerprint,
        is_draft=draft,
        draft_expires_at=timezone.now() + timedelta(minutes=timeout_minutes) if draft else None,
    )
    if not rev.is_draft:
        provision_reviews_for_revision(rev)
    print(f"{pr.formatted_id}: created revision {rev.revision_number} ({head_sha[:8]})")
