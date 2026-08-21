from django import forms

class StagingBatchFilterForm(forms.Form):
    target_owner = forms.CharField(required=False, max_length=255)
    target_owner_exact = forms.BooleanField(required=False)

    target_branch = forms.CharField(required=False, max_length=255)
    target_branch_exact = forms.BooleanField(required=False)

    pr_title = forms.CharField(required=False, max_length=255)
    pr_title_exact = forms.BooleanField(required=False)

    pr_author = forms.CharField(required=False, max_length=255)
    pr_author_exact = forms.BooleanField(required=False)

    pr_source_owner = forms.CharField(required=False, max_length=255)
    pr_source_owner_exact = forms.BooleanField(required=False)

    pr_source_repo = forms.CharField(required=False, max_length=255)
    pr_source_repo_exact = forms.BooleanField(required=False)

    pr_source_branch = forms.CharField(required=False, max_length=255)
    pr_source_branch_exact = forms.BooleanField(required=False)

    pr_target_owner = forms.CharField(required=False, max_length=255)
    pr_target_owner_exact = forms.BooleanField(required=False)

    pr_target_repo = forms.CharField(required=False, max_length=255)
    pr_target_repo_exact = forms.BooleanField(required=False)

    pr_target_branch = forms.CharField(required=False, max_length=255)
    pr_target_branch_exact = forms.BooleanField(required=False)

    def target_fields(self):
        return [
            (self['target_owner'], self['target_owner_exact']),
            (self['target_branch'], self['target_branch_exact']),
        ]

    def pr_fields(self):
        return [
            (self['pr_title'], self['pr_title_exact']),
            (self['pr_author'], self['pr_author_exact']),
        ]

    def pr_source_fields(self):
        return [
            (self['pr_source_owner'], self['pr_source_owner_exact']),
            (self['pr_source_repo'], self['pr_source_repo_exact']),
            (self['pr_source_branch'], self['pr_source_branch_exact']),
        ]

    def pr_target_fields(self):
        return [
            (self['pr_target_owner'], self['pr_target_owner_exact']),
            (self['pr_target_repo'], self['pr_target_repo_exact']),
            (self['pr_target_branch'], self['pr_target_branch_exact']),
        ]
