import uuid
from typing import Any

from django.db import models

from apps.common.encryption import EncryptedTextField
from apps.common.managers import WorkspaceScopedManager
from apps.credentials.models import PlatformCredential


class SocialAccount(models.Model):
    class ConnectionStatus(models.TextChoices):
        CONNECTED = "connected", "Connected"
        TOKEN_EXPIRING = "token_expiring", "Token Expiring"
        DISCONNECTED = "disconnected", "Disconnected"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    platform = models.CharField(
        max_length=30,
        choices=PlatformCredential.Platform.choices,
    )
    account_platform_id = models.CharField(
        max_length=255,
        help_text="The account's native ID on the platform.",
    )
    account_name = models.CharField(max_length=255)
    account_handle = models.CharField(max_length=255, blank=True, default="")
    avatar_url = models.URLField(max_length=500, blank=True, default="")
    follower_count = models.IntegerField(default=0)

    # Encrypted OAuth tokens
    oauth_access_token = EncryptedTextField(blank=True, default="")
    oauth_refresh_token = EncryptedTextField(blank=True, default="")
    token_expires_at = models.DateTimeField(blank=True, null=True)

    # Instance URL for Mastodon and Bluesky PDS
    instance_url = models.URLField(max_length=500, blank=True, default="")

    # Connection health
    connection_status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.CONNECTED,
    )
    last_health_check_at = models.DateTimeField(blank=True, null=True)
    last_error = models.TextField(blank=True, default="")

    connected_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "social_accounts_social_account"
        unique_together = [("workspace", "platform", "account_platform_id")]

    def __str__(self):
        return f"{self.account_name} ({self.get_platform_display()})"

    @property
    def is_token_expiring_soon(self) -> bool:
        """Token expires within 7 days."""
        if not self.token_expires_at:
            return False
        from datetime import timedelta

        from django.utils import timezone

        return self.token_expires_at < timezone.now() + timedelta(days=7)

    @property
    def needs_reconnect(self) -> bool:
        return self.connection_status in (
            self.ConnectionStatus.DISCONNECTED,
            self.ConnectionStatus.ERROR,
        )

    # Platform character limits
    PLATFORM_CHAR_LIMITS = {
        "facebook": 63206,
        "instagram": 2200,
        "instagram_personal": 2200,
        "linkedin_personal": 3000,
        "linkedin_company": 3000,
        "tiktok": 2200,
        "youtube": 5000,
        "pinterest": 500,
        "threads": 500,
        "bluesky": 300,
        "google_business": 1500,
        "mastodon": 500,
    }

    @property
    def char_limit(self) -> int:
        return self.PLATFORM_CHAR_LIMITS.get(self.platform, 2200)

    # Platform-specific field configuration (which platforms need extra fields)
    PLATFORM_FIELD_CONFIG: dict[str, dict[str, Any]] = {
        "youtube": {
            "needs_title": True,
            "title_max_length": 100,
            "title_label": "Video Title",
            "caption_label": "Description",
            "advanced_fields": ["made_for_kids", "privacy_status", "tags", "thumbnail"],
        },
        "pinterest": {
            "needs_title": True,
            "title_max_length": 100,
            "title_label": "Pin Title",
            "caption_label": "Description",
            "supports_first_comment": False,
            "advanced_fields": ["allow_comments", "show_similar_products", "alt_text", "cover_image"],
        },
        "tiktok": {
            "supports_first_comment": False,
        },
        "bluesky": {
            "supports_first_comment": False,
        },
        "google_business": {
            "supports_first_comment": False,
        },
    }

    PLATFORM_FIELD_DEFAULTS = {
        "needs_title": False,
        "title_max_length": 0,
        "title_label": "Title",
        "caption_label": "Caption",
        "supports_first_comment": True,
        "advanced_fields": [],
    }

    @property
    def field_config(self) -> dict:
        """Return field configuration for this platform."""
        return {**self.PLATFORM_FIELD_DEFAULTS, **self.PLATFORM_FIELD_CONFIG.get(self.platform, {})}

    @property
    def platform_icon(self) -> str:
        """Short icon label for platform badges."""
        icons = {
            "facebook": "f",
            "instagram": "ig",
            "instagram_personal": "ig",
            "linkedin_personal": "in",
            "linkedin_company": "in",
            "tiktok": "tk",
            "youtube": "yt",
            "pinterest": "pi",
            "threads": "th",
            "bluesky": "bs",
            "google_business": "gb",
            "mastodon": "ma",
        }
        return icons.get(self.platform, self.platform[:2])


class MastodonAppRegistration(models.Model):
    """Stores per-instance OAuth app registrations for Mastodon federation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance_url = models.URLField(max_length=500, unique=True)
    client_id = EncryptedTextField()
    client_secret = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "social_accounts_mastodon_app_registration"

    def __str__(self):
        return self.instance_url


class PlatformVisibility(models.Model):
    """Site-wide toggle controlling which platforms appear on the connect page."""

    platform = models.CharField(
        max_length=30,
        choices=PlatformCredential.Platform.choices,
        unique=True,
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="If unchecked, this platform is hidden from the connect page.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "social_accounts_platform_visibility"
        verbose_name = "Connect page platform"
        verbose_name_plural = "Connect page platforms"
        ordering = ["platform"]

    def __str__(self):
        return f"{self.get_platform_display()} ({'visible' if self.is_visible else 'hidden'})"
