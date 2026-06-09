"""Background workers for the Studio side of the Intelligence integration.

Three recurring/triggered tasks:

- ``provision_intelligence_account_via_session(pending_id)``, worker
  fallback when the sync activate view transient-failed. Re-runs the
  two-phase activation flow + the OrgMembership re-check before
  committing locally. Critical: the worker is the authoritative auth
  re-checker (T18 demoted-admin bypass defense).

- ``reconcile_intelligence_subscriptions()``, every 6 h. Pulls
  ``/internal/v1/accounts/{user_id}`` for every non-canceled local sub
  to catch drift (status changes, plan changes, period rollover) that
  webhook-driven state may have missed.

- ``refresh_subscription_on_visit(org_id)``, fire-and-forget; called
  at the end of the playground view to keep the local mirror fresh.
  Throttled by a cache key so a hot org doesn't generate one task per
  page render.
"""

from __future__ import annotations

import logging
from datetime import datetime

from background_task import background
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.members.models import OrgMembership

from .models import (
    IntelligenceSubscription,
    PendingActivation,
    StudioCheckoutAttempt,
)

logger = logging.getLogger(__name__)


WORKER_MAX_ATTEMPTS = 5
BACKOFF_SECONDS = [5, 30, 120, 600, 3600]  # 5s, 30s, 2m, 10m, 1h


@background(schedule=0)
def provision_intelligence_account_via_session(pending_id):
    """Worker fallback for sync activation transient failures.

    Re-runs Phase 1 + Phase 2 against Intelligence and re-checks the
    CURRENT OrgMembership of ``pending.user`` on the resolved org. A
    user who initiated checkout but was demoted before activation
    must NOT be able to commit through this path (T18).
    """
    from .services.client import InternalClient
    from .services.exceptions import (
        ActivationRejected,
        IntelligenceClientError,
        ServiceUnavailable,
    )
    from .views import _finalize_local_subscription

    # Claim the row atomically. On Postgres (Studio's prod backend),
    # ``select_for_update`` requires an open transaction or it raises
    # ``TransactionManagementError``, this used to break every worker
    # run before any work began. The lock is released when the ``with``
    # block exits so the subsequent network calls do not hold a row
    # lock during Stripe/Intelligence I/O.
    with transaction.atomic():
        try:
            pending = PendingActivation.objects.select_for_update().get(id=pending_id)
        except PendingActivation.DoesNotExist:
            logger.warning(
                "PendingActivation %s vanished before worker ran",
                pending_id,
            )
            return

        if pending.status not in (
            PendingActivation.Status.PENDING,
            PendingActivation.Status.IN_PROGRESS,
        ):
            logger.info(
                "PendingActivation %s already in terminal state %s",
                pending_id,
                pending.status,
            )
            return

        pending.status = PendingActivation.Status.IN_PROGRESS
        pending.attempts = (pending.attempts or 0) + 1
        pending.save(update_fields=["status", "attempts", "updated_at"])

    client = InternalClient()

    # Phase 1, same as the sync view, but the worker needs to derive
    # the expected_external_org_id itself. The sync view used the
    # StudioCheckoutAttempt; we have to look it up by session_id.
    attempt = StudioCheckoutAttempt.objects.filter(
        stripe_session_id=pending.session_id,
    ).first()
    if attempt is None:
        # No local attempt exists for this session, either it was
        # cleaned up by a manual operator or never written. Mark
        # provisioning_failed so the user sees a clear error.
        pending.status = PendingActivation.Status.PROVISIONING_FAILED
        pending.last_error = "no_matching_studio_checkout_attempt"
        pending.save(update_fields=["status", "last_error", "updated_at"])
        return

    try:
        preflight = client.activate_preflight(
            session_id=pending.session_id,
            expected_external_org_id=str(attempt.organization_id),
            plan_slug=attempt.plan_slug,
            billing_email=attempt.organization.billing_email or "",
            org_name=attempt.organization.name,
            contact_email=pending.user.email,
            contact_full_name=pending.user.name or "",
            idempotency_key=f"preflight-{pending.session_id}",
        )
    except ActivationRejected as exc:
        pending.status = PendingActivation.Status.PROVISIONING_FAILED
        pending.last_error = f"preflight_rejected: {exc.code or 'unknown'}"
        pending.save(update_fields=["status", "last_error", "updated_at"])
        return
    except (ServiceUnavailable, IntelligenceClientError) as exc:
        _reschedule_or_fail(pending, exc)
        return

    resolved_org_id = preflight.get("resolved_external_org_id")
    pending.resolved_organization_id = resolved_org_id
    pending.save(update_fields=["resolved_organization", "updated_at"])

    # ---- Belt-and-braces: refuse if Intelligence's resolved org id
    # disagrees with the local StudioCheckoutAttempt's organization.
    # The sync activate view does this explicitly at views.py:463-468;
    # without parity here, a buggy / compromised Intelligence service
    # could return a mismatched resolved_external_org_id and the worker
    # would proceed to commit into the wrong org. Intelligence's own
    # /activate-preflight is supposed to enforce this equality
    # server-side, but trust-but-verify is cheap.
    if str(resolved_org_id) != str(attempt.organization_id):
        pending.status = PendingActivation.Status.PROVISIONING_FAILED
        pending.last_error = (
            f"resolved_org_mismatch: intel returned {resolved_org_id!r} "
            f"but local attempt is for {attempt.organization_id!r}"
        )
        pending.save(update_fields=["status", "last_error", "updated_at"])
        logger.warning(
            "Worker resolved_org_mismatch for pending %s (attempt_org=%s resolved_org=%s)",
            pending.id,
            attempt.organization_id,
            resolved_org_id,
        )
        return

    # ---- CRITICAL: re-check current OrgMembership of pending.user ------
    # The activate view did this for the sync path; the worker MUST do
    # it too. Without this check, a captured/guessed session id forced
    # through the timeout path could provision into an org the user
    # does not currently administer.
    membership = OrgMembership.objects.filter(
        user=pending.user,
        organization_id=resolved_org_id,
        org_role__in=[OrgMembership.OrgRole.OWNER, OrgMembership.OrgRole.ADMIN],
    ).first()
    if membership is None:
        pending.status = PendingActivation.Status.REJECTED_UNAUTHORIZED
        pending.last_error = f"user no longer OWNER/ADMIN on org {resolved_org_id}"
        pending.save(update_fields=["status", "last_error", "updated_at"])
        logger.warning(
            "Worker REJECTED_UNAUTHORIZED for pending %s (user=%s org=%s)",
            pending.id,
            pending.user_id,
            resolved_org_id,
        )
        return

    # Phase 2, commit.
    try:
        commit_resp = client.activate_commit(
            validation_token=preflight["validation_token"],
            contact_email=pending.user.email,
            contact_full_name=pending.user.name or "",
            billing_email=attempt.organization.billing_email or "",
            org_name=attempt.organization.name,
            idempotency_key=f"commit-{pending.session_id}",
        )
    except ActivationRejected as exc:
        pending.status = PendingActivation.Status.PROVISIONING_FAILED
        pending.last_error = f"commit_rejected: {exc.code or 'unknown'}"
        pending.save(update_fields=["status", "last_error", "updated_at"])
        return
    except (ServiceUnavailable, IntelligenceClientError) as exc:
        _reschedule_or_fail(pending, exc)
        return

    # Final local commit. Reuse the sync view's logic so the lost-key
    # rotation path is identical.
    from django.http import HttpRequest

    fake_request = HttpRequest()
    fake_request.user = pending.user
    try:
        # _finalize_local_subscription returns a redirect Response; we
        # don't need it here, but we DO need it to run the DB writes.
        _finalize_local_subscription(
            fake_request,
            attempt=attempt,
            expected_org=attempt.organization,
            commit_resp=commit_resp,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Local finalize failed for pending %s", pending.id)
        _reschedule_or_fail(pending, exc)
        return

    pending.status = PendingActivation.Status.COMPLETED
    pending.save(update_fields=["status", "updated_at"])


def _reschedule_or_fail(pending: PendingActivation, exc: Exception):
    if pending.attempts >= WORKER_MAX_ATTEMPTS:
        pending.status = PendingActivation.Status.PROVISIONING_FAILED
        pending.last_error = f"max_attempts_exceeded: {type(exc).__name__}: {exc}"
        pending.save(update_fields=["status", "last_error", "updated_at"])
        return
    pending.status = PendingActivation.Status.PENDING
    pending.last_error = f"{type(exc).__name__}: {exc}"
    pending.save(update_fields=["status", "last_error", "updated_at"])
    delay = BACKOFF_SECONDS[min(pending.attempts - 1, len(BACKOFF_SECONDS) - 1)]
    provision_intelligence_account_via_session(str(pending.id), schedule=delay)


# ---------------------------------------------------------------------------
# Periodic reconcile
# ---------------------------------------------------------------------------


@background(schedule=0)
def reconcile_intelligence_subscriptions():
    """Catch drift between Intelligence and local IntelligenceSubscription
    rows that webhook-driven sync may have missed (e.g., a
    customer.subscription.updated webhook lost in transit).

    For each non-canceled local sub, pulls /internal/v1/accounts/{id}
    and updates the local mirror.
    """
    from .services.client import InternalClient
    from .services.exceptions import IntelligenceClientError

    client = InternalClient()
    qs = IntelligenceSubscription.objects.exclude(
        status__in=[
            IntelligenceSubscription.Status.CANCELED,
            IntelligenceSubscription.Status.PROVISIONING_FAILED,
        ],
    ).exclude(intelligence_account_id="")

    for sub in qs.iterator():
        try:
            remote = client.get_account(user_id=sub.intelligence_account_id)
        except IntelligenceClientError as exc:
            logger.warning(
                "Reconcile failed for sub %s (account %s): %s",
                sub.id,
                sub.intelligence_account_id,
                exc,
            )
            continue
        _apply_reconcile_update(sub, remote)


def _apply_reconcile_update(sub: IntelligenceSubscription, remote: dict):
    updates = {}
    if remote.get("plan_slug") and remote["plan_slug"] != sub.plan_slug:
        updates["plan_slug"] = remote["plan_slug"]
    if remote.get("status") and remote["status"] != sub.status:
        updates["status"] = remote["status"]
    if remote.get("period_end"):
        try:
            # ``django.utils.timezone`` re-exports ``datetime`` as a
            # convenience, but the django-stubs package doesn't mark it
            # as a public attribute, so mypy flags ``timezone.datetime``
            # as ``attr-defined``. Use stdlib ``datetime`` directly to
            # keep the typecheck green without losing functionality.
            period_end = datetime.fromisoformat(remote["period_end"].replace("Z", "+00:00"))
            if period_end != sub.current_period_end:
                updates["current_period_end"] = period_end
        except (ValueError, AttributeError):
            pass
    if updates:
        updates["last_synced_at"] = timezone.now()
        for k, v in updates.items():
            setattr(sub, k, v)
        sub.save(update_fields=list(updates) + ["updated_at"])


# ---------------------------------------------------------------------------
# Refresh-on-visit (throttled)
# ---------------------------------------------------------------------------


def refresh_subscription_on_visit(org_id: str):
    """Schedule a one-shot reconcile for ``org_id`` if not throttled.

    Called at the end of the playground view. The throttle (60s in
    cache) means a busy org with frequent playground hits generates at
    most one task per minute. NOT decorated with @background, it
    schedules another task that IS background.
    """
    cache_key = f"intel:refresh:{org_id}"
    if cache.get(cache_key):
        return  # Throttled, recent refresh already in flight.
    cache.set(cache_key, "1", timeout=60)
    _refresh_one_subscription(str(org_id))


@background(schedule=0)
def _refresh_one_subscription(org_id: str):
    """Background worker for refresh_subscription_on_visit."""
    from .services.client import InternalClient
    from .services.exceptions import IntelligenceClientError

    try:
        sub = IntelligenceSubscription.objects.get(organization_id=org_id)
    except IntelligenceSubscription.DoesNotExist:
        return
    if sub.status == IntelligenceSubscription.Status.CANCELED:
        return
    if not sub.intelligence_account_id:
        return

    try:
        remote = InternalClient().get_account(user_id=sub.intelligence_account_id)
    except IntelligenceClientError:
        return
    _apply_reconcile_update(sub, remote)
