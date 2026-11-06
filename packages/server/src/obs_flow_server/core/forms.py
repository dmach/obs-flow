from django import forms


class ProjectFilterForm(forms.Form):
    name = forms.CharField(required=False, max_length=255)
    name_exact = forms.BooleanField(required=False, label="Exact")

    org = forms.CharField(required=False, max_length=255)
    org_exact = forms.BooleanField(required=False, label="Exact")

    branch_name = forms.CharField(required=False, max_length=255, label="Branch")
    branch_name_exact = forms.BooleanField(required=False, label="Exact")

    workflow_type = forms.ChoiceField(
        required=False,
        choices=[("", "Any"), ("direct", "Direct"), ("staging", "Staging")],
        label="Workflow Type",
    )

    def primary_fields(self):
        return [
            (self["name"], self["name_exact"]),
            (self["org"], self["org_exact"]),
            (self["branch_name"], self["branch_name_exact"]),
            (self["workflow_type"], None),
        ]


class PackageFilterForm(forms.Form):
    project = forms.CharField(required=False, max_length=255)
    project_exact = forms.BooleanField(required=False, label="Exact")

    name = forms.CharField(required=False, max_length=255)
    name_exact = forms.BooleanField(required=False, label="Exact")

    def primary_fields(self):
        return [
            (self["project"], self["project_exact"]),
            (self["name"], self["name_exact"]),
        ]
