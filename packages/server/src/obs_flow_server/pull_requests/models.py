from django.db import models
from django.db.models import Q
from django.conf import settings

from core.models import GitMapping, Issue, Project
from reviews.models import BaseReview


class PullRequest(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        MERGED = "merged", "Merged"

    target = models.ForeignKey(GitMapping, on_delete=models.CASCADE, related_name="pull_requests")
    number = models.IntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pull_requests")
    state = models.CharField(max_length=10, choices=State.choices, default=State.OPEN)
    title = models.CharField(max_length=255, null=True, blank=True)
    is_mergeable = models.BooleanField(null=True, blank=True)
    source_owner = models.CharField(max_length=255)
    source_repo = models.CharField(max_length=255)
    source_branch = models.CharField(max_length=255)

    class Meta:
        unique_together = ("target", "number")

    @property
    def is_draft(self) -> bool:
        latest = self.revisions.order_by("-revision_number").first()
        return latest.is_draft if latest else False

    @property
    def target_project(self) -> Project:
        return self.target.target_project

    def __str__(self):
        return f"PR #{self.number} ({self.state}) on {self.target}"


class PullRequestRevision(models.Model):
    pull_request = models.ForeignKey(PullRequest, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.IntegerField()
    head_sha = models.CharField(max_length=64)  # Designed for SHA-1, SHA-256, etc.
    base_sha = models.CharField(max_length=64)
    fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    is_draft = models.BooleanField(default=False)
    draft_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("pull_request", "revision_number")

    def __str__(self):
        return f"{self.pull_request} - Rev {self.revision_number} ({self.fingerprint[:8]})"

    def get_changed_files(self) -> set[str]:
        """
        Returns the set of files changed in this revision relative to base.
        TODO: Fetch changed files directly from Git backend (Gitea API / git diff).
        """
        if hasattr(self, "_changed_files"):
            return set(self._changed_files)
        return {"src/main.py"}

    def get_inter_revision_changed_files(self, prev_revision: "PullRequestRevision | None" = None) -> set[str]:
        """
        Returns the set of files changed between prev_revision and this revision.
        TODO: Fetch diff between revisions directly from Git backend (e.g., git diff prev..curr).
        """
        if hasattr(self, "_inter_revision_changed_files"):
            return set(self._inter_revision_changed_files)
        return set()


class PullRequestRevisionIssue(models.Model):
    pull_request_revision = models.ForeignKey(
        PullRequestRevision, on_delete=models.CASCADE, related_name="revision_issues"
    )
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="revision_prs")

    class Meta:
        unique_together = ("pull_request_revision", "issue")

    def __str__(self):
        return f"{self.pull_request_revision} -> {self.issue}"


class PullRequestReview(BaseReview):
    revision = models.ForeignKey(PullRequestRevision, on_delete=models.CASCADE, related_name="reviews")

    class Meta(BaseReview.Meta):
        constraints = BaseReview.Meta.constraints + [
            models.UniqueConstraint(
                fields=["revision", "reviewer_user"],
                condition=Q(reviewer_user__isnull=False),
                name="unique_pr_review_user",
            ),
            models.UniqueConstraint(
                fields=["revision", "reviewer_group"],
                condition=Q(reviewer_group__isnull=False),
                name="unique_pr_review_group",
            ),
            models.UniqueConstraint(
                fields=["revision", "dynamic_role"],
                condition=Q(dynamic_role__isnull=False),
                name="unique_pr_review_dynamic_role",
            ),
        ]

    def __str__(self):
        reviewer = self.reviewer_user or self.reviewer_group or self.dynamic_role
        return f"Review for {self.revision}: {reviewer} ({self.state})"
