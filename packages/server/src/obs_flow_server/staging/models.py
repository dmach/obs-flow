from django.db import models
from django.db.models import Q
from django.conf import settings

from core.models import Project
from pull_requests.models import PullRequest
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

    def __str__(self):
        return f"Staging Batch #{self.id} ({self.state}) for {self.project.name}"


class StagingBatchPullRequest(models.Model):
    staging_batch = models.ForeignKey(StagingBatch, on_delete=models.CASCADE, related_name="batch_pull_requests")
    pull_request = models.ForeignKey(PullRequest, on_delete=models.CASCADE, related_name="pr_staging_batches")

    class Meta:
        unique_together = ("staging_batch", "pull_request")

    def __str__(self):
        return f"{self.staging_batch} -> {self.pull_request}"


class StagingReview(BaseReview):
    staging = models.ForeignKey(StagingBatch, on_delete=models.CASCADE, related_name="reviews")

    class Meta(BaseReview.Meta):
        constraints = BaseReview.Meta.constraints + [
            models.UniqueConstraint(
                fields=["staging", "reviewer_user"],
                condition=Q(reviewer_user__isnull=False),
                name="unique_staging_review_user",
            ),
            models.UniqueConstraint(
                fields=["staging", "reviewer_group"],
                condition=Q(reviewer_group__isnull=False),
                name="unique_staging_review_group",
            ),
            models.UniqueConstraint(
                fields=["staging", "dynamic_role"],
                condition=Q(dynamic_role__isnull=False),
                name="unique_staging_review_dynamic_role",
            ),
        ]

    def __str__(self):
        reviewer = self.reviewer_user or self.reviewer_group or self.dynamic_role
        return f"Review for {self.staging}: {reviewer} ({self.state})"
