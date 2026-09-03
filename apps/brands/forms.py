from django import forms

from .models import BrandProfile


class LineListField(forms.CharField):
    def prepare_value(self, value):
        if isinstance(value, list):
            return "\n".join(value)
        return value

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return []
        return [item.strip() for item in value.splitlines() if item.strip()]


class BrandProfileForm(forms.ModelForm):
    vocabulary = LineListField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    prohibited_terms = LineListField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    preferred_terminology = LineListField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    brand_colors = LineListField(
        required=False,
        help_text="One hexadecimal color per line, for example #1D4ED8.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    content_pillars = LineListField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    target_geographies = LineListField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    target_personas = LineListField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    class Meta:
        model = BrandProfile
        fields = [
            "name",
            "description",
            "industry",
            "target_audience",
            "brand_voice",
            "tone",
            "vocabulary",
            "prohibited_terms",
            "preferred_terminology",
            "primary_language",
            "secondary_language",
            "brand_colors",
            "positioning",
            "value_proposition",
            "content_pillars",
            "cta_strategy",
            "posting_frequency",
            "target_geographies",
            "target_personas",
            "recruiting_objective",
            "business_objective",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "target_audience": forms.Textarea(attrs={"rows": 3}),
            "brand_voice": forms.Textarea(attrs={"rows": 3}),
            "positioning": forms.Textarea(attrs={"rows": 3}),
            "value_proposition": forms.Textarea(attrs={"rows": 3}),
            "cta_strategy": forms.Textarea(attrs={"rows": 3}),
            "recruiting_objective": forms.Textarea(attrs={"rows": 3}),
            "business_objective": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.workspace = kwargs.pop("workspace")
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "rounded"
            else:
                field.widget.attrs["class"] = "form-input w-full"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicate = BrandProfile.objects.filter(workspace=self.workspace, name__iexact=name)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("A brand with this name already exists in this workspace.")
        return name

    def save(self, commit=True):
        brand = super().save(commit=False)
        brand.workspace = self.workspace
        if commit:
            brand.full_clean()
            brand.save()
        return brand
