"""API key + audit log models for the Agent API.

Keys are HMAC-hashed at rest (peppered from ``SECRET_KEY`` via the same HKDF
helper the encrypted fields use). Lookup happens in O(1) via an indexed
``lookup_prefix`` column derived from the random secret part of the token.

The plaintext token is shown to the user **once** at issuance and never stored.
"""

import uuid

from django.conf import settings
from django.db import models


class ApiKey(models.Model):
    """A scoped bearer credential used by external agents.

    Scoping:
      * One ``workspace`` — the key can only act on resources in this workspace
      * M2M to ``SocialAccount`` — explicit allowlist of which connected
        accounts the key may target. Defense-in-depth at request time checks
        every account in the allowlist still belongs to ``workspace``.
      * ``permissions`` — subset of the workspace permission catalog. The
        effective permissions on each request are the intersection of this
        list and the issuer's current ``WorkspaceMembership.effective_permissions``,
        so demoting / removing the issuer silently shrinks the key's grants.

    Token format (constructed in ``services.issue_api_key``):

        bb_studio_<random32>_<lookup8>

    Where:
      * ``random32`` — 32 url-safe bytes from ``secrets.token_urlsafe(32)``
        (~256 bits entropy); this is the only secret material.
      * ``lookup8`` — first 8 hex chars of ``sha256(random32)``; stored
        plaintext to make lookup O(1) without revealing the secret.

    At rest we only store ``lookup_prefix`` and ``token_hash`` (HMAC-SHA256
    of the random part, peppered from SECRET_KEY). A DB leak therefore leaks
    neither plaintext nor pre-image; the indexed prefix + constant-time HMAC
    compare drives the verification path.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    social_accounts = models.ManyToManyField(
        "social_accounts.SocialAccount",
        related_name="api_keys",
        help_text="Explicit allowlist of accounts this key may act on (size >= 1).",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_api_keys",
        help_text="User who issued the key. If they lose membership the key dies on next use.",
    )

    name = models.CharField(max_length=100, help_text='Human label, e.g. "Zapier bot".')
    lookup_prefix = models.CharField(max_length=16, unique=True, db_index=True)
    token_hash = models.CharField(max_length=64, help_text="HMAC-SHA256 hex digest.")
    permissions = models.JSONField(
        default=list,
        help_text="List of permission keys the holder is granted (subset of PERMISSION_KEYS).",
    )

    expires_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True, db_index=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    last_used_ip = models.GenericIPAddressField(blank=True, null=True)

    # Per-key overrides for rate-limit defaults (applied only when not null).
    # Lets an admin loosen a Pro-tier X integration's key without bumping
    # the global default for every other bot on the instance.
    rate_override_writes = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Per-minute write-rate override. Null = use platform default.",
    )
    rate_override_reads = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Per-minute read-rate override. Null = use platform default.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_keys_api_key"
        indexes = [
            models.Index(fields=["workspace", "revoked_at"], name="idx_apikey_ws_revoked"),
        ]

    def __str__(self):
        return f"{self.name} ({self.lookup_prefix})"

    @property
    def is_active(self) -> bool:
        """True iff the key is neither revoked nor past its expiry."""
        from django.utils import timezone

        if self.revoked_at is not None:
            return False
        return not (self.expires_at is not None and self.expires_at <= timezone.now())


class ApiKeyAuditLog(models.Model):
    """One row per authenticated Agent API request.

    Records *what* the key did, never *what was in the body* — request payloads
    can carry media URLs with embedded signed tokens, so we deliberately keep
    the audit row to action + target ID + status.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api_key = models.ForeignKey(
        ApiKey,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
        help_text="Set for bb_studio_ key requests; null for OAuth callers (see actor_user).",
    )
    # OAuth 2.1 MCP callers act as a *person*, not a minted key — there is no
    # ApiKey row to point at, so attribute the request to the user instead.
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="mcp_audit_logs",
        null=True,
        blank=True,
        help_text="Set for OAuth-authenticated MCP requests; null for key requests.",
    )
    actor_label = models.CharField(
        max_length=16,
        blank=True,
        default="",
        help_text='Credential type, e.g. "oauth". Empty for bb_studio_ keys.',
    )
    action = models.CharField(
        max_length=64,
        help_text='Verb + resource, e.g. "post.create", "post.cancel", "accounts.list".',
    )
    target_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="UUID of the primary resource affected (Post, PlatformPost, ...).",
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    status_code = models.PositiveSmallIntegerField()
    ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "api_keys_audit_log"
        indexes = [
            models.Index(fields=["api_key", "created_at"], name="idx_audit_key_time"),
        ]

    def __str__(self):
        actor = self.api_key.name if self.api_key_id else (self.actor_label or "oauth")
        return f"{self.action} -> {self.status_code} ({actor})"
