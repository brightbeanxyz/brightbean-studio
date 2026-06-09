"""Forms for the Post Composer."""

from django import forms

from apps.common.validators import normalize_tags, parse_and_truncate_tag_string

from .models import ContentCategory, Idea, Post, PostTemplate


class IdeaForm(forms.ModelForm):
    """Form for creating and editing ideas on the Kanban board."""

    class Meta:
        model = Idea
        fields = ["title", "description", "tags"]

    def clean_tags(self):
        tags = self.cleaned_data.get("tags") or []
        if isinstance(tags, str):
            return parse_and_truncate_tag_string(tags)
        try:
            return normalize_tags(tags)
        except ValueError as e:
            raise forms.ValidationError(str(e)) from e


class PostForm(forms.ModelForm):
    """Form for creating and editing posts in the composer."""

    # Platform selection comes from POST data as a list of social_account IDs
    selected_accounts = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        help_text="Comma-separated list of SocialAccount UUIDs.",
    )

    scheduled_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    # Override JSONField's auto-generated form field - the frontend sends tags
    # as a comma-separated string, not JSON.  clean_tags() converts to a list.
    tags = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Post
        fields = ["title", "caption", "first_comment", "internal_notes", "tags", "category"]
        widgets = {
            "caption": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Write your post caption...",
                    "class": "form-input w-full",
                    "x-model": "caption",
                    "@input.debounce.500ms": "updatePreview()",
                }
            ),
            "first_comment": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "First comment (optional)...",
                    "class": "form-input w-full",
                }
            ),
            "internal_notes": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Internal notes (not visible to clients)...",
                    "class": "form-input w-full",
                }
            ),
        }

    def clean_tags(self):
        tags = self.cleaned_data.get("tags") or []
        if isinstance(tags, str):
            return parse_and_truncate_tag_string(tags)
        try:
            return normalize_tags(tags)
        except ValueError as e:
            raise forms.ValidationError(str(e)) from e


class ContentCategoryForm(forms.ModelForm):
    """Form for creating/editing content categories."""

    class Meta:
        model = ContentCategory
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "e.g., Educational, Promotional...",
                    "class": "form-input w-full",
                }
            ),
            "color": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "w-10 h-10 rounded-lg border border-stone-200 cursor-pointer p-0.5",
                }
            ),
        }


class PostTemplateForm(forms.ModelForm):
    """Form for creating/editing post templates."""

    class Meta:
        model = PostTemplate
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Template name...",
                    "class": "form-input w-full",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Optional description...",
                    "class": "form-input w-full",
                }
            ),
        }


class PlatformOverrideForm(forms.Form):
    """Form for per-platform caption/media overrides."""

    social_account_id = forms.UUIDField(widget=forms.HiddenInput())
    platform_specific_caption = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Custom caption for this platform (leave empty to use shared caption)...",
                "class": "form-input w-full text-sm",
            }
        ),
    )
    platform_specific_first_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "Custom first comment...",
                "class": "form-input w-full text-sm",
            }
        ),
    )
