import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower

SHARED_NAME_REGEX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+:-]{0,199}$")
PERSONAL_ORG_NAME_REGEX = re.compile(r"^~[A-Za-z0-9][A-Za-z0-9._+:-]{0,198}$")
BRANCH_NAME_REGEX = re.compile(r"^[A-Za-z0-9._+-]+$")


def validate_entity_name(value: str):
    if not SHARED_NAME_REGEX.match(value):
        raise ValidationError(f"Name '{value}' must match ^[A-Za-z0-9][A-Za-z0-9._+:-]{{0,199}}$")
    if value.endswith(".git"):
        raise ValidationError(f"Name '{value}' must not end with .git")
    if ".." in value:
        raise ValidationError(f"Name '{value}' must not contain '..'")


def validate_org_name(value: str):
    if value.startswith("~"):
        if not PERSONAL_ORG_NAME_REGEX.match(value):
            raise ValidationError(f"Personal org name '{value}' must match ^~[A-Za-z0-9][A-Za-z0-9._+:-]{{0,198}}$")
    else:
        validate_entity_name(value)
    if value.endswith(".git"):
        raise ValidationError(f"Org name '{value}' must not end with .git")
    if ".." in value:
        raise ValidationError(f"Org name '{value}' must not contain '..'")


def validate_branch_name(value: str):
    if not BRANCH_NAME_REGEX.match(value):
        raise ValidationError(f"Branch name '{value}' must match ^[A-Za-z0-9._+-]+$")
    if "/" in value:
        raise ValidationError("Branch name must not contain '/'")
    if ".." in value:
        raise ValidationError("Branch name must not contain '..'")


class Org(models.Model):
    name = models.CharField(max_length=200, unique=True, validators=[validate_org_name])
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="personal_org",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_org_name_lower",
            )
        ]

    @property
    def is_personal(self) -> bool:
        return self.user_id is not None

    def clean(self):
        super().clean()
        if not self.name:
            raise ValidationError("Org name cannot be empty.")
        validate_org_name(self.name)
        if self.user_id is not None and not self.name.startswith("~"):
            raise ValidationError(f"Personal org name must start with '~' followed by username (got '{self.name}')")
        if self.user_id is None and self.name.startswith("~"):
            raise ValidationError(f"Shared org name must not start with '~' (got '{self.name}')")

    def save(self, *args, **kwargs):
        if self.pk:
            orig = Org.objects.get(pk=self.pk)
            if orig.name != self.name:
                raise ValidationError("Renaming an org is forbidden.")
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Project(models.Model):
    class WorkflowType(models.TextChoices):
        DIRECT = "direct", "Direct"
        STAGING = "staging", "Staging"

    name = models.CharField(max_length=255, unique=True, validators=[validate_entity_name])
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="projects",
        null=True,
        blank=True,
    )
    branch_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        validators=[validate_branch_name],
    )
    workflow_type = models.CharField(
        max_length=20,
        choices=WorkflowType.choices,
        default=WorkflowType.DIRECT,
    )
    review_debounce_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_project_name_lower",
            ),
            models.UniqueConstraint(
                fields=["org", "branch_name"],
                condition=Q(org__isnull=False, branch_name__isnull=False),
                name="unique_project_org_branch",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.name:
            raise ValidationError("Project name cannot be empty.")
        validate_entity_name(self.name)
        if self.branch_name:
            validate_branch_name(self.branch_name)

    def save(self, *args, **kwargs):
        if self.pk:
            orig = Project.objects.get(pk=self.pk)
            if orig.name != self.name:
                raise ValidationError("Renaming a project is forbidden.")
            if orig.branch_name and orig.branch_name != self.branch_name:
                raise ValidationError("Changing project branch name is forbidden.")
        self.clean()
        super().save(*args, **kwargs)

    @property
    def effective_review_debounce_minutes(self) -> int:
        if self.review_debounce_minutes is not None:
            return self.review_debounce_minutes
        return settings.REVIEW_DEBOUNCE_MINUTES

    def __str__(self):
        return self.name


class Package(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=255, validators=[validate_entity_name])
    forked_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forks",
    )

    class Meta:
        unique_together = ("project", "name")

    def clean(self):
        super().clean()
        if not self.name:
            raise ValidationError("Package name cannot be empty.")
        validate_entity_name(self.name)

    def save(self, *args, **kwargs):
        if self.pk:
            orig = Package.objects.get(pk=self.pk)
            if orig.name != self.name:
                raise ValidationError("Renaming a package is forbidden.")
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.name}/{self.name}"


class IssueTracker(models.Model):
    class Kind(models.TextChoices):
        OTHER = "other", "Other"
        BUGZILLA = "bugzilla", "Bugzilla"
        CVE = "cve", "CVE"
        FATE = "fate", "FATE"
        TRAC = "trac", "Trac"
        LAUNCHPAD = "launchpad", "Launchpad"
        SOURCEFORGE = "sourceforge", "SourceForge"
        GITHUB = "github", "GitHub"
        JIRA = "jira", "Jira"
        DEBBUGS = "debbugs", "Debbugs"

    name = models.CharField(max_length=50, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=500)
    show_url = models.CharField(max_length=500, null=True, blank=True)
    regex = models.CharField(max_length=255)
    label = models.TextField()

    def __str__(self):
        return self.name


class Issue(models.Model):
    issue_tracker = models.ForeignKey(IssueTracker, on_delete=models.CASCADE, related_name="issues")
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("issue_tracker", "name")

    def __str__(self):
        return f"{self.issue_tracker.name}:{self.name}"
