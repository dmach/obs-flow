from core.models import Issue, Project
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django.urls import reverse
from obs_flow_common.pull_requests import (
    pull_request_build_text_id,
    pull_request_parse_text_id,
)
from reviews.models import BaseReview


class PullRequestManager(models.Manager):
    def get_by_text_id(self, text_id: str) -> "PullRequest":
        owner, repo, number = pull_request_parse_text_id(text_id)
        qs = self.filter(project__org__name=owner, number=number)
        if repo == "_project":
            qs = qs.filter(package__isnull=True)
        else:
            qs = qs.filter(package__name=repo)
        return qs.get()


class PullRequest(models.Model):
    objects = PullRequestManager()

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

    comments = GenericRelation("core.Comment", related_query_name="pull_request")

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
    def latest_revision(self) -> "PullRequestRevision | None":
        return self.revisions.order_by("-revision_number").first()

    @property
    def text_id(self) -> str:
        return pull_request_build_text_id(self.target_owner, self.target_repo, self.number)

    @property
    def is_draft(self) -> bool:
        latest = self.latest_revision
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

    def url_for(self, route: str = "pr_detail") -> str:
        kwargs = {"project_name": self.project.name, "number": self.number}
        if self.package_id is not None:
            kwargs["package_name"] = self.package.name
        return reverse(route, kwargs=kwargs)

    def get_absolute_url(self) -> str:
        return self.url_for("pr_detail")

    @property
    def commits_url(self) -> str:
        return self.url_for("pr_commits")

    @property
    def files_changed_url(self) -> str:
        return self.url_for("pr_files_changed")

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
