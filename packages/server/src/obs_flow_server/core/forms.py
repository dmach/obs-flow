from django import forms

class GitMappingFilterForm(forms.Form):
    owner = forms.CharField(required=False, max_length=255)
    owner_exact = forms.BooleanField(required=False, label="Exact")

    repo = forms.CharField(required=False, max_length=255)
    repo_exact = forms.BooleanField(required=False, label="Exact")

    branch = forms.CharField(required=False, max_length=255)
    branch_exact = forms.BooleanField(required=False, label="Exact")

    project = forms.CharField(required=False, max_length=255)
    project_exact = forms.BooleanField(required=False, label="Exact")

    package = forms.CharField(required=False, max_length=255)
    package_exact = forms.BooleanField(required=False, label="Exact")

    def s_fields(self):
        return [
            (self['owner'], self['owner_exact']),
            (self['repo'], self['repo_exact']),
            (self['branch'], self['branch_exact']),
            (self['project'], self['project_exact']),
            (self['package'], self['package_exact']),
        ]
