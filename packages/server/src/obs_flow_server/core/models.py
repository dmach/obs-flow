from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower


class Project(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Package(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("project", "name")

    def __str__(self):
        return f"{self.project.name}/{self.name}"


class GitMapping(models.Model):
    owner = models.CharField(max_length=255)
    repo = models.CharField(max_length=255)
    branch = models.CharField(max_length=255)
    project = models.OneToOneField(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="git_mapping"
    )
    package = models.OneToOneField(
        Package, on_delete=models.SET_NULL, null=True, blank=True, related_name="git_mapping"
    )

    class Meta:
        constraints = [
            # UniqueConstraint using Lower('owner') and Lower('repo') with branch
            models.UniqueConstraint(
                Lower("owner"),
                Lower("repo"),
                "branch",
                name="unique_git_mapping_branch",
            ),
            # CheckConstraint (XOR): Exactly one of project or package MUST be set
            models.CheckConstraint(
                condition=(
                    Q(project__isnull=False, package__isnull=True) | Q(project__isnull=True, package__isnull=False)
                ),
                name="git_mapping_xor_project_package",
            ),
        ]

    def __str__(self):
        target = self.project or self.package
        return f"{self.owner}/{self.repo}:{self.branch} -> {target}"


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
