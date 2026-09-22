from urllib.parse import urlsplit

from django import forms
from django.utils import timezone

from .models import AIProviderConfiguration, Campaign, ContentPlan, GenerationRequest, VisualBrief


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

    def __init__(self, *args, provider_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if provider_choices is not None:
            self.fields["provider"].choices = provider_choices
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input w-full"


class AIProviderConfigurationForm(forms.ModelForm):
    class Meta:
        model = AIProviderConfiguration
        fields = ["api_key", "default_model", "base_url", "is_enabled", "daily_request_limit", "timeout_seconds", "max_retries"]
        widgets = {"api_key": forms.PasswordInput(render_value=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["api_key"].required = False
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-input w-full"

    def clean_base_url(self):
        base_url = self.cleaned_data.get("base_url", "").strip()
        if not base_url:
            return ""
        host = (urlsplit(base_url).hostname or "").lower()
        allowed_hosts = {
            GenerationRequest.Provider.OPENAI: {"api.openai.com"},
            GenerationRequest.Provider.OPENROUTER: {"openrouter.ai"},
            GenerationRequest.Provider.AGNES: {"apihub.agnes-ai.com"},
            GenerationRequest.Provider.OLLAMA: {"localhost", "127.0.0.1", "::1"},
        }
        provider_hosts = allowed_hosts.get(self.instance.provider, set())
        if host not in provider_hosts:
            raise forms.ValidationError("This provider URL is not in the security allowlist.")
        return base_url.rstrip("/")


class VisualBriefForm(forms.ModelForm):
    colors_text = forms.CharField(required=False, label="Colors", help_text="Comma-separated brand colors.")

    class Meta:
        model = VisualBrief
        fields = ["provider", "model", "objective", "style", "format", "constraints"]
        widgets = {
            "objective": forms.Textarea(attrs={"rows": 4}),
            "constraints": forms.Textarea(attrs={"rows": 3}),
            "format": forms.Select(choices=[("square", "Square"), ("portrait", "Portrait"), ("landscape", "Landscape")]),
        }

    def __init__(self, *args, provider_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if provider_choices is not None:
            self.fields["provider"].choices = provider_choices
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input w-full"

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.colors = [value.strip() for value in self.cleaned_data.get("colors_text", "").split(",") if value.strip()]
        if commit:
            instance.save()
        return instance


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "brand", "description", "status", "starts_at", "ends_at"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "starts_at": forms.DateInput(attrs={"type": "date"}),
            "ends_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = self.fields["brand"].queryset.filter(workspace=workspace)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input w-full"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("starts_at") and cleaned.get("ends_at") and cleaned["ends_at"] < cleaned["starts_at"]:
            raise forms.ValidationError("Campaign end date cannot precede its start date.")
        return cleaned
