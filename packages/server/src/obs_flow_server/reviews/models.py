import fnmatch
from django.db import models
from django.db.models import Q
from django.conf import settings

from core.models import Project, Package


class ReviewScope(models.Model):
    # Names of reserved/built-in scopes that cannot be modified or deleted.
    RESERVED_NAMES = frozenset({"global"})

    name = models.CharField(max_length=100, unique=True)
    include_globs = models.JSONField(default=list)
    exclude_globs = models.JSONField(default=list)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.name in self.RESERVED_NAMES and not self._state.adding:
            raise ValueError(f"The '{self.name}' scope is reserved and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.name in self.RESERVED_NAMES:
            raise ValueError(f"The '{self.name}' scope is reserved and cannot be deleted.")
        return super().delete(*args, **kwargs)

    @staticmethod
    def matches_glob(filepath: str, pattern: str) -> bool:
        """
        Checks if a filepath matches a glob pattern.
        Handles recursive matching ('**/*'), basename matching, and directory prefixes.
        """
        if fnmatch.fnmatch(filepath, pattern):
            return True
        if "/" not in pattern and fnmatch.fnmatch(filepath.split("/")[-1], pattern):
            return True
        return False

    def is_file_in_scope(self, filepath: str) -> bool:
        """
        Determines if a file is in review scope:
        A file is considered in-scope if it matches at least one include glob
        AND does not match any exclude glob.
        """
        included = any(self.matches_glob(filepath, pat) for pat in self.include_globs)
        if not included:
            return False
        excluded = any(self.matches_glob(filepath, pat) for pat in self.exclude_globs)
        if excluded:
            return False
        return True

    def get_files_in_scope(self, files: set[str] | list[str]) -> set[str]:
        """
        Filters the given files and returns only those that fall within the specified scope.
        """
        return {f for f in files if self.is_file_in_scope(f)}

    def evaluate(self, files: set[str] | list[str]) -> bool:
        """
        Evaluates whether the scope is triggered by any file in the given set of files.
        Returns True if at least one file is in-scope.
        """
        return len(self.get_files_in_scope(files)) > 0


class ReviewConfigBase(models.Model):
    class ConfigType(models.TextChoices):
        PROJECT = "project", "Project"
        PACKAGE = "package", "Package"
        STAGING = "staging", "Staging"

    class DynamicRole(models.TextChoices):
        MAINTAINER = "maintainer", "Maintainer"

    type = models.CharField(max_length=10, choices=ConfigType.choices)
    scope = models.ForeignKey(
        ReviewScope,
        on_delete=models.PROTECT,
        related_name="%(class)s_configs",
    )
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
    depends_on = models.ManyToManyField(
        "self",
        symmetrical=False,
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

    def validate_no_cycles(self, new_dependencies=None) -> None:
        """
        Validates that new_dependencies (or self.depends_on) do not form a cycle in the DAG.
        Raises ValueError if a circular dependency is detected.
        """
        if new_dependencies is None:
            new_dependencies = self.depends_on.all() if self.pk else []

        visited = set()
        stack = list(new_dependencies)
        while stack:
            current = stack.pop()
            if self.pk and current.pk == self.pk:
                reviewer = self.reviewer_user or self.reviewer_group or self.dynamic_role
                raise ValueError(
                    f"Circular dependency detected: '{reviewer}' cannot depend on itself directly or indirectly."
                )
            if current.pk not in visited:
                visited.add(current.pk)
                stack.extend(current.depends_on.all())



class ReviewConfig(ReviewConfigBase):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="review_configurations")

    class Meta(ReviewConfigBase.Meta):
        constraints = ReviewConfigBase.Meta.constraints + [
            models.UniqueConstraint(
                fields=["project", "type", "reviewer_user"],
                condition=Q(reviewer_user__isnull=False),
                name="unique_project_type_reviewer_user",
            ),
            models.UniqueConstraint(
                fields=["project", "type", "reviewer_group"],
                condition=Q(reviewer_group__isnull=False),
                name="unique_project_type_reviewer_group",
            ),
            models.UniqueConstraint(
                fields=["project", "type", "dynamic_role"],
                condition=Q(dynamic_role__isnull=False),
                name="unique_project_type_dynamic_role",
            ),
        ]

    def __str__(self):
        reviewer = self.reviewer_user or self.reviewer_group or self.dynamic_role
        return f"Config for {self.project.name}: {reviewer} ({self.type})"


class ReviewConfigOverride(ReviewConfigBase):
    class Mode(models.TextChoices):
        ADD = "add", "Add"
        REMOVE = "remove", "Remove"

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="review_overrides")
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.ADD)

    class Meta(ReviewConfigBase.Meta):
        constraints = ReviewConfigBase.Meta.constraints + [
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
    depends_on = models.ManyToManyField(
        "self",
        symmetrical=False,
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

    @property
    def reviewer_name(self) -> str:
        if self.reviewer_user_id:
            return self.reviewer_user.username
        if self.reviewer_group_id:
            return self.reviewer_group.name
        return self.dynamic_role or ""

    def unblock_downstream_reviews(self) -> list["BaseReview"]:
        """
        When this review is resolved (ACCEPTED or OVERRIDDEN), inspects downstream
        reviews that depend on it. If all their prerequisites are resolved,
        transitions them from WAITING to PENDING.
        """
        unblocked = []
        rel_name = f"{self.__class__.__name__.lower()}_dependents"
        if not hasattr(self, rel_name):
            return unblocked

        dependents = getattr(self, rel_name).all()
        for dep in dependents:
            if dep.state == self.State.WAITING:
                prereqs = dep.depends_on.all()
                if prereqs.exists() and all(p.state in (self.State.ACCEPTED, self.State.OVERRIDDEN) for p in prereqs):
                    dep.state = self.State.PENDING
                    dep.save(update_fields=["state"])
                    unblocked.append(dep)

        return unblocked

    def propagate_decision(self) -> list["BaseReview"]:
        """
        Propagates a decision on a review forward:
        When a review is decided at revision N, the decision propagates forward
        to every later revision with is_inherited = True, storing it on each,
        and stops at the first revision where is_inherited = False.
        """
        propagated = []
        rev = self.revision
        model_class = self.__class__
        rev_model_class = rev.__class__

        if hasattr(rev, "pull_request"):
            parent_filter = {"pull_request": rev.pull_request}
        elif hasattr(rev, "staging_batch"):
            parent_filter = {"staging_batch": rev.staging_batch}
        else:
            return propagated

        later_revs = rev_model_class.objects.filter(
            **parent_filter,
            revision_number__gt=rev.revision_number,
        ).order_by("revision_number")

        for later_rev in later_revs:
            later_review = model_class.objects.filter(
                revision=later_rev,
                reviewer_user=self.reviewer_user,
                reviewer_group=self.reviewer_group,
                dynamic_role=self.dynamic_role,
                scope=self.scope,
            ).first()

            if not later_review or not later_review.is_inherited:
                break

            later_review.state = self.state
            later_review.actor = self.actor
            later_review.justification = self.justification
            later_review.save()
            propagated.append(later_review)

        return propagated

    def save(self, *args, **kwargs):
        is_resolved = self.state in (self.State.ACCEPTED, self.State.OVERRIDDEN)
        is_raw = kwargs.get("raw", False)
        super().save(*args, **kwargs)
        if is_resolved and self.pk and not is_raw:
            self.unblock_downstream_reviews()
