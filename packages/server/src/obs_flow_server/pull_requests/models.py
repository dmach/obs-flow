from django.db import models
from django.db.models import Q
from django.conf import settings

from core.models import Issue, Project
from reviews.models import BaseReview


class PullRequest(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        MERGED = "merged", "Merged"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="pull_requests")
    package = models.ForeignKey("core.Package", on_delete=models.CASCADE, related_name="pull_requests", null=True, blank=True)
    number = models.IntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pull_requests")
    state = models.CharField(max_length=10, choices=State.choices, default=State.OPEN)
    title = models.CharField(max_length=255, null=True, blank=True)
    is_mergeable = models.BooleanField(null=True, blank=True)
    source_owner = models.CharField(max_length=255)
    source_repo = models.CharField(max_length=255)
    source_branch = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "package", "number"],
                name="unique_pull_request_project_package_number",
            ),
            models.UniqueConstraint(
                fields=["project", "number"],
                condition=Q(package__isnull=True),
                name="unique_pull_request_project_number_null_package",
            ),
        ]

    @property
    def is_draft(self) -> bool:
        latest = self.revisions.order_by("-revision_number").first()
        return latest.is_draft if latest else False

    @property
    def target(self):
        return None

    @property
    def target_project(self) -> Project:
        return self.project

    @property
    def target_package(self):
        return self.package

    @property
    def target_owner(self) -> str:
        return self.project.org.name if self.project and self.project.org else ""

    @property
    def target_repo(self) -> str:
        return self.package.name if self.package else "_project"

    @property
    def target_branch(self) -> str:
        return self.project.branch_name if self.project else ""

    @property
    def formatted_id(self) -> str:
        return f"{self.target_owner}/{self.target_repo}#{self.number}"

    def __str__(self):
        return f"{self.formatted_id} ({self.state}) - {self.title}"


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
