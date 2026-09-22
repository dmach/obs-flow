from django import forms
from accounts.models import UserPreferences

class PreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = ["theme", "font_size", "page_size"]
        widgets = {
            "theme": forms.Select(attrs={"class": "form-control"}),
            "font_size": forms.NumberInput(attrs={"min": 12, "max": 20, "class": "form-control"}),
            "page_size": forms.NumberInput(attrs={"min": 100, "max": 1000, "class": "form-control"}),
        }

    def clean_font_size(self):
        font_size = self.cleaned_data.get("font_size")
        if font_size < 12 or font_size > 20:
            raise forms.ValidationError("Font size must be between 12 and 20.")
        return font_size

    def clean_page_size(self):
        page_size = self.cleaned_data.get("page_size")
        if page_size < 100 or page_size > 1000:
            raise forms.ValidationError("Page size must be between 100 and 1000.")
        return page_size
