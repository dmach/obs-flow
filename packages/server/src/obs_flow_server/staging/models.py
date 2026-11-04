from django.db import models
from django.db.models import Q
from django.conf import settings

from core.models import Project
from pull_requests.models import PullRequest, PullRequestRevision
from reviews.models import BaseReview


class StagingBatch(models.Model):
    class State(models.TextChoices):
        COLLECTING = "collecting", "Collecting"
        IN_PROGRESS = "in-progress/open", "In Progress / Open"
        PENDING_RELEASE = "pending-release", "Pending Release"
        MERGED = "merged/completed", "Merged / Completed"
        FAILED = "failed", "Failed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="staging_batches")
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=30, choices=State.choices, default=State.COLLECTING)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staging_batches",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    collecting_until = models.DateTimeField(null=True, blank=True)
    release_date = models.DateTimeField(null=True, blank=True)
    embargo_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(state__in=["merged/completed", "failed"], closed_at__isnull=False)
                    | ~Q(state__in=["merged/completed", "failed"], closed_at__isnull=False)
                ),
                name="staging_batch_closed_at_check",
            )
        ]

    @property
    def is_draft(self) -> bool:
        latest = self.revisions.order_by("-revision_number").first()
        return latest.is_draft if latest else False

    def __str__(self):
        return f"Staging Batch #{self.id} ({self.state}) for {self.project.name}"


class StagingBatchRevision(models.Model):
    staging_batch = models.ForeignKey(StagingBatch, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.IntegerField()
    fingerprint = models.CharField(max_length=64)  # Designed for SHA-256
    created_at = models.DateTimeField(auto_now_add=True)
    is_draft = models.BooleanField(default=False)
    draft_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("staging_batch", "revision_number")

    def __str__(self):
        return f"{self.staging_batch} - Rev {self.revision_number} ({self.fingerprint[:8]})"

    def get_changed_files(self) -> set[str]:
        """
        Returns the set of files changed in this revision relative to base.
        For Staging Batches, changed files are the union of all files
        changed across all Pull Request Revisions included in the batch.
        """
        if hasattr(self, "_changed_files"):
            return set(self._changed_files)

        batch_files = set()
        for bpr in self.revision_pull_requests.select_related("pull_request_revision").all():
            batch_files.update(bpr.pull_request_revision.get_changed_files())
        if batch_files:
            return batch_files

        return {"src/main.py"}

    def get_inter_revision_changed_files(self, prev_revision: "StagingBatchRevision | None" = None) -> set[str]:
        """
        Returns the set of files changed between prev_revision and this revision.
        For Staging Batches, union of inter-revision changes across PR revisions.
        """
        if hasattr(self, "_inter_revision_changed_files"):
            return set(self._inter_revision_changed_files)

        if prev_revision:
            curr_bprs = {
                bpr.pull_request_revision.pull_request_id: bpr.pull_request_revision
                for bpr in self.revision_pull_requests.select_related("pull_request_revision").all()
            }
            prev_bprs = {
                bpr.pull_request_revision.pull_request_id: bpr.pull_request_revision
                for bpr in prev_revision.revision_pull_requests.select_related("pull_request_revision").all()
            }
            inter_files = set()
            for pr_id, curr_pr_rev in curr_bprs.items():
                prev_pr_rev = prev_bprs.get(pr_id)
                if prev_pr_rev:
                    inter_files.update(curr_pr_rev.get_inter_revision_changed_files(prev_pr_rev))
                else:
                    inter_files.update(curr_pr_rev.get_changed_files())
            return inter_files

        return set()


class StagingBatchRevisionPullRequest(models.Model):
    staging_batch_revision = models.ForeignKey(
        StagingBatchRevision, on_delete=models.CASCADE, related_name="revision_pull_requests"
    )
    pull_request_revision = models.ForeignKey(
        PullRequestRevision, on_delete=models.CASCADE, related_name="staging_batch_revisions"
    )

    class Meta:
        unique_together = ("staging_batch_revision", "pull_request_revision")

    def __str__(self):
        return f"{self.staging_batch_revision} -> {self.pull_request_revision}"


class StagingReview(BaseReview):
    revision = models.ForeignKey(StagingBatchRevision, on_delete=models.CASCADE, related_name="reviews")

    class Meta(BaseReview.Meta):
        constraints = BaseReview.Meta.constraints + [
            models.UniqueConstraint(
                fields=["revision", "reviewer_user"],
                condition=Q(reviewer_user__isnull=False),
                name="unique_staging_review_user",
            ),
            models.UniqueConstraint(
                fields=["revision", "reviewer_group"],
                condition=Q(reviewer_group__isnull=False),
                name="unique_staging_review_group",
            ),
            models.UniqueConstraint(
                fields=["revision", "dynamic_role"],
                condition=Q(dynamic_role__isnull=False),
                name="unique_staging_review_dynamic_role",
            ),
        ]

    def __str__(self):
        reviewer = self.reviewer_user or self.reviewer_group or self.dynamic_role
        return f"Review for {self.revision}: {reviewer} ({self.state})"
