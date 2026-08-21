from django import forms

class PullRequestFilterForm(forms.Form):
    title = forms.CharField(required=False, max_length=255)
    title_exact = forms.BooleanField(required=False)

    author = forms.CharField(required=False, max_length=255)
    author_exact = forms.BooleanField(required=False)

    in_progress_days = forms.IntegerField(required=False, min_value=0)

    source_owner = forms.CharField(required=False, max_length=255)
    source_owner_exact = forms.BooleanField(required=False)

    source_repo = forms.CharField(required=False, max_length=255)
    source_repo_exact = forms.BooleanField(required=False)

    source_branch = forms.CharField(required=False, max_length=255)
    source_branch_exact = forms.BooleanField(required=False)

    target_owner = forms.CharField(required=False, max_length=255)
    target_owner_exact = forms.BooleanField(required=False)

    target_repo = forms.CharField(required=False, max_length=255)
    target_repo_exact = forms.BooleanField(required=False)

    target_branch = forms.CharField(required=False, max_length=255)
    target_branch_exact = forms.BooleanField(required=False)

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
