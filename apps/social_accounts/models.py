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
    avatar_url = models.URLField(max_length=2000, blank=True, default="")
    follower_count = models.IntegerField(default=0)

    # Encrypted OAuth tokens
    oauth_access_token = EncryptedTextField(blank=True, default="")
    oauth_refresh_token = EncryptedTextField(blank=True, default="")
    token_expires_at = models.DateTimeField(blank=True, null=True)

    # Instance URL for Mastodon and Bluesky PDS
    instance_url = models.URLField(max_length=500, blank=True, default="")

    # Object we subscribed for webhook delivery, when it isn't this account
    # itself. Instagram accounts connected via Facebook Login receive their
    # comment and message events through the linked Page, so this holds that
    # Page ID — needed to unsubscribe cleanly on disconnect.
    webhook_target_id = models.CharField(max_length=255, blank=True, default="")

    # Whether the platform is currently pushing this account's activity to us.
    # Null means "not applicable" (the platform has no webhooks) or "not tried
    # yet". False means the inbox will miss comments and mentions, which is
    # invisible without saying so — publishing and analytics still work, so the
    # connection itself stays healthy and `last_error` (owned by the periodic
    # health check) must not be borrowed for it.
    webhooks_active = models.BooleanField(null=True, blank=True, default=None)
    webhook_error = models.CharField(max_length=500, blank=True, default="")
    # Set when the subscription failed for a reason a retry cannot fix: the
    # grant itself is missing what it needs. Splits the card's CTA between
    # "Try again" (re-run the call) and "Reconnect" (get a new grant), so the
    # warning never asks for something the UI doesn't offer.
    webhook_needs_reconnect = models.BooleanField(default=False)
    # The provider's own words about the last failure. `webhook_error` is
    # rewritten for a human and is all the card shows; operators running
    # `diagnose_facebook` need the error code and fbtrace_id this keeps.
    webhook_error_detail = models.TextField(blank=True, default="")
    # Consecutive failed attempts, so the periodic health check can stop
    # re-trying a subscription that will never succeed. Reset by a success, by
    # a reconnect, and by the user pressing "Try again".
    webhook_retry_count = models.PositiveSmallIntegerField(default=0)

    # Scopes we asked for that the grant came back without. Meta drops
    # unapproved or declined permissions silently rather than failing the
    # grant, so without this the account looks healthy and only breaks later at
    # publish or insights time with an opaque platform error. Empty means
    # "everything we asked for was granted", or that the platform gives us no
    # way to ask.
    missing_scopes = models.JSONField(default=list, blank=True)

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

    # Per-account override of the Agent-API platform daily-post quota
    # (see apps/api/limits.py::PLATFORM_DAILY_POST_LIMIT). Null = use the
    # platform default. Useful when one specific integration is on a higher
    # upstream tier (e.g. an X account on Pro vs the default Basic cap).
    daily_post_limit_override = models.PositiveIntegerField(blank=True, null=True)

    # Set by the analytics sync layer when the platform rejects an analytics
    # call as insufficient-scope. Surfaces a "Reconnect for analytics" CTA in
    # place of the metric region. Cleared on successful reconnect.
    analytics_needs_reconnect = models.BooleanField(default=False)

    # When the inbox last polled this account, and when it last walked the
    # account's full history. Both belong here rather than being derived from
    # InboxMessage.received_at, which answers a different question: an account
    # that was polled and had nothing new to say leaves no message behind, so
    # the derived value would say "never polled" and re-poll it every cycle.
    #
    # The poll stamp is what lets one 5-minute cycle serve platforms with very
    # different budgets — see settings.INBOX_PLATFORM_MIN_POLL_SECONDS. The
    # sweep stamp paces the deep walk that catches a reply on a thread too old
    # for the routine poll's lookback (providers.youtube.get_messages).
    inbox_last_polled_at = models.DateTimeField(blank=True, null=True)
    inbox_last_deep_sweep_at = models.DateTimeField(blank=True, null=True)
    inbox_initial_backfill_cursor = models.TextField(blank=True, default="")
    inbox_initial_backfill_started_at = models.DateTimeField(blank=True, null=True)
    inbox_deep_sweep_cursor = models.TextField(blank=True, default="")
    inbox_deep_sweep_started_at = models.DateTimeField(blank=True, null=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "social_accounts_social_account"
        unique_together = [("workspace", "platform", "account_platform_id")]

    def __str__(self):
        return f"{self.account_name} ({self.get_platform_display()})"

    @property
    def display_label(self) -> str:
        """Human name for pickers and filters: the account name, else the handle.

        Mirrors the ``account_name|default:account_handle`` the channel filters
        used inline, so a component that can only read one attribute (the
        ``ui_select`` tag's ``label_field``) still renders the same text.
        """
        return self.account_name or self.account_handle

    def token_expires_within(self, window) -> bool:
        """Whether the recorded expiry falls inside ``window`` from now.

        An unknown expiry (``token_expires_at is None``) answers False: we
        cannot judge it, and the platforms where "unknown" should mean "refresh
        anyway" are named explicitly in ``tasks.EXPIRY_BOOTSTRAP_PLATFORMS``.

        The window is a caller's decision because it means different things at
        different cadences. A user-triggered publish can afford the generous
        7-day view. An hourly background loop cannot: a Google access token
        lives one hour, so *any* window wider than that is permanently true and
        would spend a refresh call every hour on every account for nothing.
        """
        if not self.token_expires_at:
            return False
        from django.utils import timezone

        return self.token_expires_at < timezone.now() + window

    @property
    def is_token_expiring_soon(self) -> bool:
        """Token expires within 7 days."""
        from datetime import timedelta

        return self.token_expires_within(timedelta(days=7))

    @property
    def needs_reconnect(self) -> bool:
        return self.connection_status in (
            self.ConnectionStatus.DISCONNECTED,
            self.ConnectionStatus.ERROR,
        )

    def refresh_oauth_token(self, provider, *, enqueue_backfill: bool = True) -> str:
        """Refresh this account's OAuth access token via *provider* and persist it.

        Returns the new access token. Propagates whatever the provider's
        ``refresh_token`` raises so callers decide between degrading (publish
        engine keeps the old token) and aborting (composer endpoints 502).

        ``enqueue_backfill=False`` is for scheduled analytics refreshes. The
        token rotation itself is enough for that sync pass; queueing the
        ``oauth_access_token`` post-save signal as well would start a duplicate
        full backfill every time an hourly run refreshes a near-expiry token.
        """
        from datetime import timedelta

        from django.utils import timezone

        new_tokens = provider.refresh_token(self.oauth_refresh_token)
        self.oauth_access_token = new_tokens.access_token
        if new_tokens.refresh_token:
            self.oauth_refresh_token = new_tokens.refresh_token
        if new_tokens.expires_in:
            self.token_expires_at = timezone.now() + timedelta(seconds=new_tokens.expires_in)
        self.connection_status = self.ConnectionStatus.CONNECTED
        update_fields = [
            "oauth_access_token",
            "oauth_refresh_token",
            "token_expires_at",
            "connection_status",
            "updated_at",
        ]
        if enqueue_backfill:
            self.save(update_fields=update_fields)
        else:
            # post_save signals do not receive caller-local keyword arguments.
            # A short-lived instance flag keeps the token in the normal
            # update_fields path while telling analytics.signals that this save
            # is already part of the analytics pass.
            self._skip_analytics_backfill = True
            try:
                self.save(update_fields=update_fields)
            finally:
                del self._skip_analytics_backfill
        return new_tokens.access_token

    # Platform character limits
    PLATFORM_CHAR_LIMITS = {
        "facebook": 63206,
        "instagram": 2200,
        "instagram_login": 2200,
        "linkedin_personal": 3000,
        "linkedin_company": 3000,
        "tiktok": 2200,
        "youtube": 5000,
        "pinterest": 500,
        "threads": 500,
        "bluesky": 300,
        "google_business": 1500,
        "mastodon": 500,
        "devto": 25000,
    }

    @property
    def char_limit(self) -> int:
        return self.PLATFORM_CHAR_LIMITS.get(self.platform, 2200)

    @property
    def escaped_chars(self) -> str:
        """Characters this platform escapes, each costing two against the limit."""
        from providers import CAPTION_ESCAPED_CHARS

        return CAPTION_ESCAPED_CHARS.get(self.platform, "")

    def caption_wire_length(self, text: str) -> int:
        """Caption length as this platform counts it, after any escaping.

        LinkedIn escapes reserved characters in the commentary it publishes, so
        the typed length is not the length that counts against ``char_limit``.
        """
        from providers import caption_wire_length

        return caption_wire_length(self.platform, text)

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
        "devto": {
            "needs_title": True,
            "title_max_length": 128,
            "title_label": "Article Title",
            "caption_label": "Body (Markdown)",
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
    def keeps_platform_grant_on_disconnect(self) -> bool:
        """True when disconnecting here cannot revoke the platform's grant.

        The Facebook-Page flows share one grant across every Page and Instagram
        account that person connected, so the only endpoint that would revoke
        it takes all of them down at once — see
        ``FacebookProvider.revoke_token``. Instagram Login is excluded: its
        token belongs to the one account, so disconnect does revoke it.
        """
        return self.platform in {
            PlatformCredential.Platform.FACEBOOK,
            PlatformCredential.Platform.INSTAGRAM,
        }

    @property
    def revokes_platform_grant_on_disconnect(self) -> bool:
        """True when disconnecting also revokes our access on the platform.

        The disconnect confirmation promises exactly this, so it lists only the
        providers whose ``revoke_token`` calls a revocation endpoint with the
        token disconnect hands it. Left out, besides the Facebook-Page flows:
        Pinterest, Threads and DEV.to have no revocation call, and Bluesky's
        ``deleteSession`` wants the refresh JWT rather than the access JWT it
        gets — and the app password outlives any session regardless.
        """
        return self.platform in {
            PlatformCredential.Platform.YOUTUBE,
            PlatformCredential.Platform.GOOGLE_BUSINESS,
            PlatformCredential.Platform.TIKTOK,
            PlatformCredential.Platform.LINKEDIN_PERSONAL,
            PlatformCredential.Platform.LINKEDIN_COMPANY,
            PlatformCredential.Platform.MASTODON,
            PlatformCredential.Platform.INSTAGRAM_LOGIN,
        }

    @property
    def revocation_token(self) -> str:
        """The token disconnect should hand the provider's ``revoke_token``.

        Google refuses to revoke an expired access token, and ours lives an
        hour, so by the time someone disconnects it is usually dead and the
        grant would survive. The refresh token revokes the same grant and
        outlives it.
        """
        if (
            self.platform
            in {
                PlatformCredential.Platform.YOUTUBE,
                PlatformCredential.Platform.GOOGLE_BUSINESS,
            }
            and self.oauth_refresh_token
        ):
            return self.oauth_refresh_token
        return self.oauth_access_token

    def supports_first_comment(self) -> bool:
        """Whether this account can have a first comment posted by the worker.

        Most platforms answer purely from PLATFORM_FIELD_CONFIG. LinkedIn Personal
        is the exception: in OIDC mode the socialActions.CREATE endpoint returns
        403 ACCESS_DENIED because that endpoint is gated on Community Management
        API approval. Resolve credentials and check ``_oauth_mode`` for it.
        """
        if not self.field_config.get("supports_first_comment", True):
            return False
        if self.platform == "linkedin_personal":
            from apps.publisher.engine import _resolve_publish_credentials

            creds = _resolve_publish_credentials(self)
            if creds.get("_oauth_mode", "oidc") == "oidc":
                return False
        return True

    @property
    def platform_icon(self) -> str:
        """Short icon label for platform badges."""
        icons = {
            "facebook": "f",
            "instagram": "ig",
            "instagram_login": "ig",
            "linkedin_personal": "in",
            "linkedin_company": "in",
            "tiktok": "tk",
            "youtube": "yt",
            "pinterest": "pi",
            "threads": "th",
            "bluesky": "bs",
            "google_business": "gb",
            "mastodon": "ma",
            "devto": "dv",
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

    @classmethod
    def visible_choices(cls) -> list[tuple[str, str]]:
        """``Platform.choices`` minus the platforms an admin has hidden.

        The single source for "what can be connected" — the connect page and
        the sidebar's connect shortcuts both read it, so they can't drift
        (the sidebar used to keep its own hand-maintained copy, which had
        fallen behind by two platforms). Platforms without a row default to
        visible, matching ``is_visible``.
        """
        hidden = set(cls.objects.filter(is_visible=False).values_list("platform", flat=True))
        return [(value, label) for value, label in PlatformCredential.Platform.choices if value not in hidden]


class AnalyticsPlatformConfig(models.Model):
    """Site-wide toggle controlling which platforms are enabled for the
    Analytics feature.

    App-review timelines for the new analytics scopes (Meta, TikTok) are
    unpredictable, so admins flip platforms on as their approvals land. If
    no rows have ``is_enabled=True`` the Analytics sidebar item is hidden
    entirely (see ``apps.common.context_processors.sidebar_context``).
    """

    platform = models.CharField(
        max_length=30,
        choices=PlatformCredential.Platform.choices,
        unique=True,
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="If unchecked, this platform is excluded from the Analytics feature.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Not a column: ``apps.analytics.signals.stash_previous_enabled`` writes the
    # stored ``is_enabled`` here on pre_save so post_save can spot an off → on
    # flip. Declared so that write type-checks; ``None`` means "not stashed",
    # which is what the post_save reader already defaults to.
    _previously_enabled: bool | None = None

    class Meta:
        db_table = "social_accounts_analytics_platform_config"
        verbose_name = "Analytics platform"
        verbose_name_plural = "Analytics platforms"
        ordering = ["platform"]

    def __str__(self):
        return f"{self.get_platform_display()} ({'enabled' if self.is_enabled else 'disabled'})"

    @classmethod
    def enabled_platforms(cls) -> list[str]:
        """Return the list of platform slugs with analytics enabled.

        A platform with no row counts as enabled, matching ``is_enabled``'s
        default and the fact that the admin forbids adding or deleting rows —
        so a missing row always means "nothing has been said about this
        platform", never "an admin turned it off". Without that, every platform
        slug added after the seed migration (``devto`` was the first) had its
        analytics silently switched off, which is invisible from the admin
        because the platform isn't listed there either.

        Driven off ``Platform.choices`` rather than the table, so a row left
        behind by a renamed slug can't leak into the result.
        """
        rows = dict(cls.objects.values_list("platform", "is_enabled"))
        return [value for value, _label in PlatformCredential.Platform.choices if rows.get(value, True)]
