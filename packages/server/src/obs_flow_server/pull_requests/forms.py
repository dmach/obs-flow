from django import forms

class PullRequestFilterForm(forms.Form):
    title = forms.CharField(required=False, max_length=255)
    title_exact = forms.BooleanField(required=False, label="Exact")

    author = forms.CharField(required=False, max_length=255)
    author_exact = forms.BooleanField(required=False, label="Exact")

    in_progress_days = forms.IntegerField(required=False, min_value=0)

    source_owner = forms.CharField(required=False, max_length=255)
    source_owner_exact = forms.BooleanField(required=False, label="Exact")

    source_repo = forms.CharField(required=False, max_length=255)
    source_repo_exact = forms.BooleanField(required=False, label="Exact")

    source_branch = forms.CharField(required=False, max_length=255)
    source_branch_exact = forms.BooleanField(required=False, label="Exact")

    target_owner = forms.CharField(required=False, max_length=255)
    target_owner_exact = forms.BooleanField(required=False, label="Exact")

    target_repo = forms.CharField(required=False, max_length=255)
    target_repo_exact = forms.BooleanField(required=False, label="Exact")

    target_branch = forms.CharField(required=False, max_length=255)
    target_branch_exact = forms.BooleanField(required=False, label="Exact")

    reviewer_person = forms.CharField(required=False, max_length=255, label="Reviewer Person")
    reviewer_person_include_groups = forms.BooleanField(required=False, label="Include Groups")

    reviewer_group = forms.CharField(required=False, max_length=255, label="Reviewer Group")

    def primary_fields(self):
        return [
            (self['title'], self['title_exact']),
            (self['author'], self['author_exact']),
            (self['in_progress_days'], None),
        ]

    def source_fields(self):
        return [
            (self['source_owner'], self['source_owner_exact']),
            (self['source_repo'], self['source_repo_exact']),
            (self['source_branch'], self['source_branch_exact']),
        ]

    def target_fields(self):
        return [
            (self['target_owner'], self['target_owner_exact']),
            (self['target_repo'], self['target_repo_exact']),
            (self['target_branch'], self['target_branch_exact']),
        ]

    def reviewer_fields(self):
        return [
            (self['reviewer_person'], self['reviewer_person_include_groups']),
            (self['reviewer_group'], None),
        ]


class PullRequestCreateForm(forms.Form):
    target_project = forms.CharField(max_length=255)
    target_package = forms.CharField(required=False, max_length=255, help_text="Leave empty for a project-level pull request.")
    title = forms.CharField(max_length=255)
    source_owner = forms.CharField(max_length=255)
    source_repo = forms.CharField(max_length=255)
    source_branch = forms.CharField(max_length=255)
    is_draft = forms.BooleanField(required=False, label="Create as draft")

    def clean(self):
        from django.core.exceptions import ValidationError
        from core.git_forge import get_repo_path
        from core.models import Package, Project, validate_entity_name, validate_org_name
        from pull_requests.services import _rev_parse_branch

        cleaned = super().clean()
        if self.errors:
            return cleaned

        project = Project.objects.select_related("org").filter(name=cleaned["target_project"]).first()
        if project is None:
            self.add_error("target_project", f"Project '{cleaned['target_project']}' does not exist.")
            return cleaned
        package = None
        if cleaned["target_package"]:
            package = Package.objects.filter(project=project, name=cleaned["target_package"]).first()
            if package is None:
                self.add_error("target_package", f"Package '{cleaned['target_package']}' does not exist in '{project.name}'.")
                return cleaned

        owner, repo, branch = cleaned["source_owner"], cleaned["source_repo"], cleaned["source_branch"]
        try:
            validate_org_name(owner)
        except ValidationError as e:
            self.add_error("source_owner", e)
        try:
            validate_entity_name(repo)
        except ValidationError as e:
            self.add_error("source_repo", e)
        if self.errors:
            return cleaned

        head = _rev_parse_branch(get_repo_path(owner, repo), branch)
        if not head:
            self.add_error("source_branch", f"Branch '{branch}' not found in {owner}/{repo}.")
            return cleaned

        target_owner = project.org.name if project.org else ""
        target_branch = project.branch_name or "main"
        base = _rev_parse_branch(get_repo_path(target_owner, package.name if package else None), target_branch)
        if head == base:
            self.add_error(None, "Source branch has no changes relative to the target branch.")

        cleaned["target_project_obj"] = project
        cleaned["target_package_obj"] = package
        return cleaned
