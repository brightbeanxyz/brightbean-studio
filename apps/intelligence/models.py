"""Models backing the Studio side of the Intelligence integration.

Three roles:

- ``IntelligenceSubscription`` (one per Org): the canonical local record
  of a Studio-provisioned Intelligence subscription. Holds the encrypted
  API key Studio uses to call Intelligence's /v1/* tool endpoints.
- ``StudioCheckoutAttempt`` (one in-flight per Org via partial unique):
  the local mirror of Intelligence's checkout-attempt row. Reserved BEFORE
  the Intelligence call so two admins racing Subscribe cannot both pay.
- ``PendingActivation`` (one per worker fallback): used when sync
  activation in the success view fails or the user closes the tab
  mid-redirect. The worker re-runs Phase 1 + Phase 2 + re-checks
  OrgMembership before committing locally.
- ``IntelligenceUsageEvent``: post-call local audit. Authoritative
  credit/plan state lives on Intelligence; this is just "which Studio
  user pressed which button at what time".
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.common.encryption import EncryptedTextField

# ---------------------------------------------------------------------------
# IntelligenceSubscription, one per Organization
# ---------------------------------------------------------------------------


class IntelligenceSubscription(models.Model):
    """One row per Studio Organization with an Intelligence subscription.

    Status lifecycle:
    - provisioning : in-request sync setup (never visible to users, the
                     activate view holds the request until it flips).
    - finalizing   : paid + sync setup failed → background worker is
                     completing. UI shows a polling overlay.
    - active       : fully provisioned, tools usable.
    - past_due     : Stripe couldn't charge, Studio learns via /v1/me.
    - canceled     : user canceled via Stripe Portal.
    - provisioning_failed : terminal failure after the worker's backoff
                            retries exhaust.
    """

    class Status(models.TextChoices):
        PROVISIONING = "provisioning", "Provisioning"
        FINALIZING = "finalizing", "Finalizing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        PROVISIONING_FAILED = "provisioning_failed", "Provisioning failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="intelligence_subscription",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PROVISIONING,
        db_index=True,
    )
    plan_slug = models.SlugField(max_length=64, blank=True, default="")

    # Stripe ids (display + audit only, Studio never calls Stripe directly).
    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=255, blank=True, default="")

    # Intelligence-side identifiers.
    intelligence_account_id = models.CharField(max_length=64, blank=True, default="")
    # Encrypted at rest. Assign plaintext to this field directly, the
    # EncryptedTextField wraps encrypt/decrypt; calling encrypt() manually
    # would double-encrypt.
    intelligence_api_key = EncryptedTextField(blank=True, default="")
    # First 8 chars of the plaintext, kept unencrypted so we can show
    # ``bb_xxxxxx...`` in the dashboard without a decrypt round-trip.
    intelligence_api_key_prefix = models.CharField(max_length=8, blank=True, default="")

    current_period_end = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    provisioning_attempts = models.IntegerField(default=0)
    last_provisioning_error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intelligence_subscription"

    def __str__(self):
        return f"IntelligenceSubscription({self.organization_id}, {self.status})"


# ---------------------------------------------------------------------------
# StudioCheckoutAttempt, financial-correctness backstop
# ---------------------------------------------------------------------------


class StudioCheckoutAttempt(models.Model):
    """Local mirror of Intelligence's ``StudioCheckoutAttempt``.

    Reserved BEFORE the Intelligence ``/studio-checkout-session`` call:

    - On the Studio side, the partial unique on
      ``(organization) WHERE status IN ('creating','open','pending')``
      blocks two concurrent admins from both reaching Intelligence (the
      financial-correctness backstop). The same constraint exists on the
      Intelligence side; this side prevents one admin from getting that
      far in the first place.
    - ``status='creating'`` indicates the Intelligence call is in flight
      and we don't yet have a checkout_url to resume. Other callers
      see this and render a polling UI ("Setting up your checkout,
      please wait") rather than mistakenly believing the URL was lost.
    - ``status='open'`` means the Stripe Checkout URL is ready and the
      attempt can be resumed by anyone with org admin permission.
    """

    class Status(models.TextChoices):
        CREATING = "creating", "Creating"
        OPEN = "open", "Open"
        PENDING = "pending", "Pending"
        ACTIVATED = "activated", "Activated"
        EXPIRED = "expired", "Expired"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="intelligence_checkout_attempts",
    )
    # The user who initiated the checkout. Recorded for audit + so we can
    # show "your finance admin started a checkout, resume?" UI to other
    # admins; the activate view does NOT trust this for authorization
    # (only current OrgMembership matters).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intelligence_checkout_attempts",
    )
    plan_slug = models.SlugField(max_length=64)
    billing_email = models.EmailField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CREATING,
    )
    stripe_session_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )
    # Stripe's hosted Checkout URL includes the session id PLUS a long
    # base64-ish fragment carrying the client_secret + payment_page state
    # — total length runs ~500-1000+ characters. Django's URLField defaults
    # to max_length=200, which silently truncates Postgres writes and raises
    # ``psycopg.errors.StringDataRightTruncation`` on save. 2000 is enough
    # headroom for any Stripe URL we've seen and is the de-facto convention
    # for URL columns in Django apps that talk to Stripe.
    checkout_url = models.URLField(max_length=2000, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "intelligence_studio_checkout_attempt"
        constraints = [
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(status__in=["creating", "open", "pending"]),
                name="intel_studio_attempt_one_in_progress_per_org",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"StudioCheckoutAttempt({self.organization_id}, {self.status})"


# ---------------------------------------------------------------------------
# PendingActivation, worker fallback
# ---------------------------------------------------------------------------


class PendingActivation(models.Model):
    """Persisted state for the worker fallback when sync activation
    transient-fails.

    Holds enough info to re-run Phase 1 + Phase 2 from a worker process
    without needing the original request context. Notably the
    ``user`` FK so the worker can re-check the CURRENT
    ``OrgMembership(pending.user, resolved_org).org_role`` before
    committing, initiator-only authorization is rejected; if the user
    was demoted between checkout and activation completion, the worker
    refuses to write the local IntelligenceSubscription.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        REJECTED_UNAUTHORIZED = "rejected_unauthorized", "Rejected (unauthorized)"
        PROVISIONING_FAILED = "provisioning_failed", "Provisioning failed"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="intelligence_pending_activations",
    )
    session_id = models.CharField(max_length=255, unique=True)
    # Set by the worker after Phase 1 returns; NULL means org is not yet
    # resolved.
    resolved_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intelligence_pending_activations",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intelligence_pending_activation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PendingActivation({self.user_id}, {self.status})"


# ---------------------------------------------------------------------------
# IntelligenceUsageEvent, local audit log
# ---------------------------------------------------------------------------


class IntelligenceUsageEvent(models.Model):
    """Per-call audit row.

    Intelligence is the authoritative source of truth for credits, plan
    state, and per-tool usage. This row exists so Studio admins can
    answer "who in our org used Intelligence today" without round-tripping
    to Intelligence for every dashboard render. Workspace is nullable
    because some tools (subscription management) aren't workspace-scoped.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="intelligence_usage_events",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intelligence_usage_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intelligence_usage_events",
    )
    endpoint = models.CharField(max_length=64)
    credits_charged = models.IntegerField(default=0)
    status_code = models.IntegerField()
    latency_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "intelligence_usage_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
        ]
