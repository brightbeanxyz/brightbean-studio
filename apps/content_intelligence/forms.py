from django import forms
from django.utils import timezone

from .models import ContentPlan, GenerationRequest


class ContentPlanForm(forms.Form):
    cadence = forms.ChoiceField(choices=ContentPlan.Cadence.choices)
    start_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input w-full"


class GenerationForm(forms.Form):
    PLATFORM_CHOICES = [
        ("linkedin", "LinkedIn"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("threads", "Threads"),
        ("x", "X / Twitter"),
        ("tiktok", "TikTok"),
    ]
    CONTENT_TYPE_CHOICES = [
        ("post", "Social post"),
        ("caption", "Caption"),
        ("thread", "Thread"),
        ("video_script", "Video script"),
    ]
    provider = forms.ChoiceField(choices=GenerationRequest.Provider.choices)
    model = forms.CharField(required=False, max_length=120, help_text="Leave blank to use the provider default.")
    platform = forms.ChoiceField(choices=PLATFORM_CHOICES)
    content_type = forms.ChoiceField(choices=CONTENT_TYPE_CHOICES)
    audience = forms.CharField(required=False, max_length=500)
    instruction = forms.CharField(
        required=False,
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text="Describe the topic, goal, offer, or constraints for this draft.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input w-full"
