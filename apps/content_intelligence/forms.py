from django import forms
from django.utils import timezone

from .models import ContentPlan


class ContentPlanForm(forms.Form):
    cadence = forms.ChoiceField(choices=ContentPlan.Cadence.choices)
    start_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input w-full"
