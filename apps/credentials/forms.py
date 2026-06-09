from django import forms
from django.utils.safestring import mark_safe

from .models import REQUIRED_CREDENTIAL_KEYS, PlatformCredential, derive_is_configured

# Human-readable required-key hints, shown under the credentials field in the
# admin. Mirrors what each provider reads (see providers/*.py).
_KEY_HINTS = {
    "facebook": "client_id, client_secret (app_id / app_secret also accepted)",
    "instagram": "client_id, client_secret (app_id / app_secret also accepted)",
    "instagram_login": "client_id, client_secret (app_id / app_secret also accepted)",
    "threads": "client_id, client_secret (app_id / app_secret also accepted)",
    "pinterest": "client_id, client_secret (app_id / app_secret also accepted)",
    "tiktok": "client_key, client_secret  (note: client_key, NOT client_id)",
    "youtube": "client_id, client_secret",
    "google_business": "client_id, client_secret (optional: account_id, location_id)",
    "linkedin_personal": "client_id, client_secret (optional: _oauth_mode = oidc | community_management)",
    "linkedin_company": "client_id, client_secret",
}

CREDENTIALS_HELP = mark_safe(
    'JSON object of app credentials, e.g. <code>{"client_id": "...", "client_secret": "..."}</code>. '
    "Required keys per platform:<br>"
    + "<br>".join(f"<b>{platform}</b>: {hint}" for platform, hint in _KEY_HINTS.items())
)


class PlatformCredentialAdminForm(forms.ModelForm):
    # Override the EncryptedJSONField (a bare TextField) with a real JSON field so
    # the admin renders/parses proper JSON instead of a Python repr — without this
    # a no-edit save would store a corrupt JSON-encoded string.
    credentials = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8, "cols": 60}),
        help_text=CREDENTIALS_HELP,
    )

    class Meta:
        model = PlatformCredential
        fields = ("organization", "platform", "credentials")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only offer platforms that take app-level credentials (exclude session /
        # per-instance auth platforms like bluesky and mastodon).
        self.fields["platform"].choices = [
            choice
            for choice in self.fields["platform"].choices
            if choice[0] == "" or choice[0] in REQUIRED_CREDENTIAL_KEYS
        ]

    def clean_credentials(self):
        data = self.cleaned_data.get("credentials")
        if data in (None, ""):
            return {}
        if not isinstance(data, dict):
            raise forms.ValidationError(
                'Credentials must be a JSON object, e.g. {"client_id": "...", "client_secret": "..."}.'
            )
        cleaned = {}
        for key, value in data.items():
            if value is None:
                continue
            text = value if isinstance(value, str) else str(value)
            if text.strip():
                cleaned[key] = text
        return cleaned

    def clean(self):
        cleaned = super().clean()
        platform = cleaned.get("platform")
        credentials = cleaned.get("credentials") or {}
        if platform and credentials and not derive_is_configured(platform, credentials):
            required = REQUIRED_CREDENTIAL_KEYS.get(platform, ())
            hint = ", ".join(" / ".join(group) for group in required)
            self.add_error(
                "credentials",
                f"Missing required keys for {platform}. Expected: {hint or 'none'}. "
                "Fill in every required key — the row stays inactive until they are all present.",
            )
        return cleaned
