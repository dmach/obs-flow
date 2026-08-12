from django.db import models
from django.db.models import Q
from django.conf import settings

from core.models import Project, Package


class ReviewConfigurationBase(models.Model):
    class ConfigType(models.TextChoices):
        PROJECT = "project", "Project"
        PACKAGE = "package", "Package"
        STAGING = "staging", "Staging"

    class DynamicRole(models.TextChoices):
        MAINTAINER = "maintainer", "Maintainer"

    type = models.CharField(max_length=10, choices=ConfigType.choices)
    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(class)s_reviewer_users",
    )
    reviewer_group = models.ForeignKey(
        "accounts.Group",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(class)s_reviewer_groups",
    )
    dynamic_role = models.CharField(
        max_length=50,
        choices=DynamicRole.choices,
        null=True,
        blank=True,
    )
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_dependents",
    )

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(reviewer_user__isnull=False, reviewer_group__isnull=True, dynamic_role__isnull=True) |
                    Q(reviewer_user__isnull=True, reviewer_group__isnull=False, dynamic_role__isnull=True) |
                    Q(reviewer_user__isnull=True, reviewer_group__isnull=True, dynamic_role__isnull=False)
                ),
                name="%(class)s_reviewer_xor",
            )
        ]


class ReviewConfiguration(ReviewConfigurationBase):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="review_configurations")

    class Meta(ReviewConfigurationBase.Meta):
        constraints = ReviewConfigurationBase.Meta.constraints + [
            models.UniqueConstraint(
                fields=["project", "reviewer_user"],
                condition=Q(reviewer_user__isnull=False),
                name="unique_project_reviewer_user",
            ),
            models.UniqueConstraint(
                fields=["project", "reviewer_group"],
                condition=Q(reviewer_group__isnull=False),
                name="unique_project_reviewer_group",
            ),
            models.UniqueConstraint(
                fields=["project", "dynamic_role"],
                condition=Q(dynamic_role__isnull=False),
                name="unique_project_dynamic_role",
            ),
        ]

    def __str__(self):
        reviewer = self.reviewer_user or self.reviewer_group or self.dynamic_role
        return f"Config for {self.project.name}: {reviewer} ({self.type})"


class ReviewConfigurationOverride(ReviewConfigurationBase):
    class Mode(models.TextChoices):
        ADD = "add", "Add"
        REMOVE = "remove", "Remove"

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="review_overrides")
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.ADD)

    class Meta(ReviewConfigurationBase.Meta):
        constraints = ReviewConfigurationBase.Meta.constraints + [
            models.CheckConstraint(
                condition=~Q(mode="remove", depends_on__isnull=False),
                name="override_remove_no_depends_on",
            ),
            models.UniqueConstraint(
                fields=["package", "reviewer_user"],
                condition=Q(reviewer_user__isnull=False),
                name="unique_package_reviewer_user",
            ),
            models.UniqueConstraint(
                fields=["package", "reviewer_group"],
                condition=Q(reviewer_group__isnull=False),
                name="unique_package_reviewer_group",
            ),
            models.UniqueConstraint(
                fields=["package", "dynamic_role"],
                condition=Q(dynamic_role__isnull=False),
                name="unique_package_dynamic_role",
            ),
        ]

    def __str__(self):
        reviewer = self.reviewer_user or self.reviewer_group or self.dynamic_role
        return f"Override for {self.package}: {self.mode} {reviewer}"


class BaseReview(models.Model):
    class State(models.TextChoices):
        WAITING = "waiting", "Waiting"
        PENDING = "pending", "Pending"
        NEEDINFO = "needinfo", "Need Info"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        OVERRIDDEN = "overridden", "Overridden"

    class DynamicRole(models.TextChoices):
        MAINTAINER = "maintainer", "Maintainer"

    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(class)s_assigned_users",
    )
    reviewer_group = models.ForeignKey(
        "accounts.Group",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(class)s_assigned_groups",
    )
    dynamic_role = models.CharField(
        max_length=50,
        choices=DynamicRole.choices,
        null=True,
        blank=True,
    )
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_dependents",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_actions",
    )
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.WAITING,
    )
    justification = models.TextField(null=True, blank=True)
    external_review_url = models.URLField(max_length=500, null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_locks",
    )
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(reviewer_user__isnull=False, reviewer_group__isnull=True, dynamic_role__isnull=True) |
                    Q(reviewer_user__isnull=True, reviewer_group__isnull=False, dynamic_role__isnull=True) |
                    Q(reviewer_user__isnull=True, reviewer_group__isnull=True, dynamic_role__isnull=False)
                ),
                name="%(class)s_reviewer_xor",
            ),
            models.CheckConstraint(
                condition=(
                    Q(state__in=["waiting", "pending"], actor__isnull=True) |
                    ~Q(state__in=["waiting", "pending"], actor__isnull=True)
                ),
                name="%(class)s_actor_state_check",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(state__in=["needinfo", "rejected", "overridden"]) |
                    Q(state__in=["needinfo", "rejected", "overridden"], justification__isnull=False)
                ),
                name="%(class)s_justification_required",
            ),
            models.CheckConstraint(
                condition=(
                    Q(locked_by__isnull=True, locked_until__isnull=True) |
                    Q(locked_by__isnull=False, locked_until__isnull=False)
                ),
                name="%(class)s_lock_fields_check",
            ),
        ]
