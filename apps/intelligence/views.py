"""Studio views for the Intelligence integration.

URL surface:

- ``/orgs/<org_id>/intelligence/``                     : playground
- ``/orgs/<org_id>/intelligence/subscribe/``           : plan picker
- ``/orgs/<org_id>/intelligence/checkout/?plan=<slug>``: TX1+TX2 checkout
- ``/orgs/<org_id>/intelligence/recover/``             : closed-tab recovery
- ``/orgs/<org_id>/intelligence/portal/``              : Stripe portal redirect
- ``/orgs/<org_id>/intelligence/billing-settings/``    : edit billing contact
- ``/orgs/<org_id>/intelligence/billing-contact/``     : POST update
- ``/orgs/<org_id>/intelligence/status/``              : HTMX polling fragment
- ``/orgs/<org_id>/intelligence/score-packaging/``     : tool POST (HTMX)
- ``/orgs/<org_id>/intelligence/score-video-hook/``    : tool POST (HTMX)
- ``/orgs/<org_id>/intelligence/benchmark-channel/``   : tool POST (HTMX)
- ``/orgs/<org_id>/intelligence/benchmark-video/``     : tool POST (HTMX)
- ``/orgs/<org_id>/intelligence/research-content-gaps/``: tool POST (HTMX)
- ``/orgs/<org_id>/intelligence/list-niches/``         : tool POST (HTMX)
- ``/intelligence/activate/?session_id=cs_…``          : Stripe success URL
- ``/intelligence/finalizing/``                        : fallback polling page
- ``/intelligence/finalizing/status/``                 : finalizing polling fragment
"""

from __future__ import annotations

import contextlib
import logging
import time
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.members.decorators import require_org_permission
from apps.members.models import OrgMembership, has_org_permission

from .decorators import intelligence_subscription_required
from .models import (
    IntelligenceSubscription,
    IntelligenceUsageEvent,
    PendingActivation,
    StudioCheckoutAttempt,
)
from .services.cache import per_request_cache
from .services.client import IntelligenceAPIClient, InternalClient
from .services.exceptions import (
    ActivationRejected,
    Conflict,
    DeploymentNotAuthorized,
    InsufficientCredits,
    IntelligenceClientError,
    RateLimited,
    ServiceUnavailable,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _client() -> InternalClient:
    return InternalClient()


def _api_client_for(sub: IntelligenceSubscription) -> IntelligenceAPIClient | None:
    if not sub or not sub.intelligence_api_key:
        return None
    return IntelligenceAPIClient(api_key=sub.intelligence_api_key)


def _me_for(request, org_id, sub: IntelligenceSubscription | None) -> dict | None:
    if not sub or sub.status != "active":
        return None
    api = _api_client_for(sub)
    if api is None:
        return None
    try:
        return per_request_cache(request, (str(org_id), "me"), api.me)
    except IntelligenceClientError:
        logger.exception("Intelligence /v1/me failed; suppressing")
        return None


# Cache the niche catalog at the Django-cache layer (not the per-request
# cache used by ``_me_for``) because:
#   1. Niches are globally consistent, every org sees the same list, so
#      a single global cache key is correct.
#   2. ``/v1/research/niches`` charges 1 credit per call. Caching for an
#      hour means the playground renders charge the org once per hour
#      instead of once per render.
#   3. The niche taxonomy turns over on Intelligence's training-pipeline
#      cadence (weekly-ish), so a 1-hour TTL is plenty fresh.
_NICHE_CACHE_KEY = "intelligence:niches"
_NICHE_CACHE_TTL_SECONDS = 60 * 60  # 1 hour


def _niches_for(sub: IntelligenceSubscription | None) -> list[dict] | None:
    """Return the niche catalog for the playground's content-gaps panel.

    Pulls from Django's cache when possible; on miss, makes one billed
    call to /v1/research/niches and stores the result. Returns ``None``
    on transient API failure so the template can degrade gracefully to
    a plain text input.
    """
    from django.core.cache import cache

    cached = cache.get(_NICHE_CACHE_KEY)
    if cached is not None:
        return cached

    if not sub or sub.status != "active":
        return None
    api = _api_client_for(sub)
    if api is None:
        return None
    try:
        resp = api.list_niches()
    except IntelligenceClientError:
        logger.exception("/v1/research/niches failed; suppressing")
        return None

    niches = resp.get("niches") if isinstance(resp, dict) else None
    if not isinstance(niches, list):
        return None
    cache.set(_NICHE_CACHE_KEY, niches, _NICHE_CACHE_TTL_SECONDS)
    return niches


def _record_usage(*, organization, user, endpoint, status_code, credits_charged=0, latency_ms=None):
    IntelligenceUsageEvent.objects.create(
        organization=organization,
        user=user if user.is_authenticated else None,
        endpoint=endpoint,
        status_code=status_code,
        credits_charged=credits_charged,
        latency_ms=latency_ms,
    )


def _render_tool_error(request, exc: IntelligenceClientError, *, organization):
    """Map a typed client error to the right HTMX result partial."""
    context = {"organization": organization, "code": exc.code, "message": str(exc)}
    status = exc.status_code or 500
    if isinstance(exc, InsufficientCredits):
        template = "intelligence/_tool_error_no_credits.html"
    elif isinstance(exc, RateLimited):
        context["retry_after"] = exc.retry_after
        template = "intelligence/_tool_error_rate_limited.html"
    elif isinstance(exc, ServiceUnavailable):
        template = "intelligence/_tool_error_unavailable.html"
    else:
        template = "intelligence/_tool_error.html"
    return render(request, template, context, status=status)


# ---------------------------------------------------------------------------
# Playground (overview)
# ---------------------------------------------------------------------------


@require_org_permission("use_intelligence")
def playground(request, org_id):
    """Single Intelligence UI surface. Always renders the playground
    layout; overlays / disabled state reflect ``IntelligenceSubscription``."""
    sub = getattr(request.org, "intelligence_subscription", None)
    me = _me_for(request, org_id, sub)

    can_manage_billing = has_org_permission(
        request.org_membership,
        "manage_intelligence_billing",
    )

    # Closed-tab recovery: only check Intelligence if we have no local sub
    # AND the user can manage billing (only they'd see the banner).
    pending = None
    if sub is None and can_manage_billing:
        try:
            pending = _client().pending_activation(external_org_id=str(org_id))
        except (ServiceUnavailable, DeploymentNotAuthorized, IntelligenceClientError):
            logger.exception("/pending-activation lookup failed; suppressing")
            pending = None

    # Preview mode = the org has no active subscription. In that case
    # we render the playground as a fully interactive showcase: every
    # panel pre-fills realistic inputs and the result area shows a
    # canned example via the SAME result partial that a real API call
    # would render, so users see exactly what they get before they
    # pay. The paywall fires only when they actually click a submit
    # button (server-side ``@intelligence_subscription_required``).
    is_preview = sub is None or sub.status != "active"

    if is_preview:
        from . import preview_data

        preview_inputs = preview_data.PREVIEW_INPUTS
        preview_results = preview_data.PREVIEW_RESULTS
        # Skip the billed /v1/research/niches call in preview mode,
        # render the combobox against a fixed sample so the UX is the
        # same shape as the live one.
        content_gap_niches = preview_results["list_niches"]["niches"]
    else:
        preview_inputs = None
        preview_results = None
        # Niche catalog for the content-gaps panel's combobox.
        # Best-effort, if Intelligence is unreachable the template
        # falls back to a free-form text input.
        content_gap_niches = _niches_for(sub)

    context = {
        "organization": request.org,
        "subscription": sub,
        "pending_activation": pending,
        "me": me,
        "can_manage_billing": can_manage_billing,
        "content_gap_niches": content_gap_niches,
        "is_preview": is_preview,
        "preview_inputs": preview_inputs,
        "preview_results": preview_results,
    }
    response = render(request, "intelligence/playground.html", context)
    # Throttled background refresh, keeps the local mirror fresh without
    # one task per page render.
    if sub and sub.status == IntelligenceSubscription.Status.ACTIVE:
        try:
            from .tasks import refresh_subscription_on_visit

            refresh_subscription_on_visit(org_id)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to schedule refresh_subscription_on_visit")
    return response


# ---------------------------------------------------------------------------
# Subscribe / checkout
# ---------------------------------------------------------------------------


@require_org_permission("manage_intelligence_billing")
def subscribe(request, org_id):
    """Plan picker + billing-contact form. Performs a local eligibility
    survey first so a user with an existing pending/active sub is routed
    to the appropriate resume/manage UI instead of being allowed to pay."""
    sub = getattr(request.org, "intelligence_subscription", None)
    if sub is not None and sub.status == IntelligenceSubscription.Status.ACTIVE:
        return redirect("intelligence:playground", org_id=org_id)
    if sub is not None and sub.status == IntelligenceSubscription.Status.FINALIZING:
        return redirect("intelligence:playground", org_id=org_id)

    # Look for an in-progress local attempt; if found, render "Resume" UI.
    resumable = (
        StudioCheckoutAttempt.objects.filter(
            organization=request.org,
            status=StudioCheckoutAttempt.Status.OPEN,
        )
        .order_by("-created_at")
        .first()
    )

    in_flight = (
        StudioCheckoutAttempt.objects.filter(
            organization=request.org,
            status=StudioCheckoutAttempt.Status.CREATING,
        )
        .order_by("-created_at")
        .first()
    )

    # Cross-check with Intelligence so a checkout URL we never persisted
    # locally (e.g. Studio crashed between Stripe.create returning and
    # the TX2 save, or a sibling Studio deployment shares the same DB
    # but the local row got deleted) still surfaces as a resume CTA
    # rather than a fresh "Subscribe" the user can double-pay through.
    if resumable is None and in_flight is None:
        try:
            remote = _client().check_eligibility(external_org_id=str(org_id))
        except (DeploymentNotAuthorized, IntelligenceClientError):
            remote = {"eligible": True}
        if not remote.get("eligible", True):
            details = remote.get("details") or {}
            if remote.get("reason") == "open_checkout" and details.get("checkout_url"):
                # Surface as a resumable attempt for the template, same
                # data shape so the existing UI handles it without
                # branching.
                resumable = StudioCheckoutAttempt(
                    organization=request.org,
                    stripe_session_id=details.get("stripe_session_id") or "",
                    checkout_url=details["checkout_url"],
                    status=StudioCheckoutAttempt.Status.OPEN,
                )
            elif remote.get("reason") in ("already_active", "pending_activation"):
                # Edge case: Intelligence sees an active/pending sub
                # that Studio's local mirror doesn't (race or drift).
                # Send the user to the playground rather than letting
                # them pay again, the next playground render will
                # pick up the live state via /v1/me.
                return redirect("intelligence:playground", org_id=org_id)

    try:
        plans_resp = _client().list_plans()
    except DeploymentNotAuthorized:
        return render(
            request,
            "intelligence/deployment_not_authorized.html",
            {"organization": request.org},
            status=403,
        )
    except IntelligenceClientError:
        logger.exception("/plans fetch failed")
        plans_resp = {"plans": []}

    context = {
        "organization": request.org,
        "plans": plans_resp.get("plans", []),
        "resumable_attempt": resumable,
        "in_flight_attempt": in_flight,
        "billing_email": request.org.billing_email or request.user.email,
    }
    return render(request, "intelligence/subscribe.html", context)


@require_POST
@require_org_permission("manage_intelligence_billing")
def checkout(request, org_id):
    """Two-transaction checkout-session creation.

    TX1: reserve local StudioCheckoutAttempt (creating) under the
    partial-unique constraint. Concurrent admins racing both get this
    far, the second hits IntegrityError and gets routed to "Resume".

    Outside TX: call Intelligence /studio-checkout-session.

    TX2: update local attempt with stripe_session_id + checkout_url +
    status=open. 302 to Stripe.
    """
    plan_slug = (request.POST.get("plan") or "").strip()
    if not plan_slug:
        return HttpResponseBadRequest("plan required")

    billing_email = (request.POST.get("billing_email") or "").strip()
    if billing_email and request.org.billing_email != billing_email:
        request.org.billing_email = billing_email
        request.org.save(update_fields=["billing_email", "updated_at"])
    billing_email = request.org.billing_email or request.user.email

    org_name = request.org.name
    user = request.user
    idempotency_key = f"checkout-{request.org.id}-{plan_slug}"

    # ---- TX1: reserve local attempt ------------------------------------
    try:
        with transaction.atomic():
            attempt = StudioCheckoutAttempt.objects.create(
                organization=request.org,
                user=user,
                plan_slug=plan_slug,
                billing_email=billing_email,
                idempotency_key=idempotency_key,
                status=StudioCheckoutAttempt.Status.CREATING,
            )
    except IntegrityError:
        # Another admin (or a previous attempt that hasn't terminated)
        # already holds the partial-unique slot. Redirect to /subscribe/,
        # which re-queries for the existing attempt and renders the
        # right "Resume your checkout" / "Setting up…" panel based on
        # its current status. We don't need to look the row up here
        # because the redirected view does that.
        return redirect("intelligence:subscribe", org_id=org_id)

    # ---- Outside any transaction: Intelligence call --------------------
    try:
        resp = _client().studio_checkout_session(
            external_org_id=str(request.org.id),
            org_name=org_name,
            billing_email=billing_email,
            plan_slug=plan_slug,
            contact_email=user.email,
            contact_full_name=user.name or "",
            return_base_url=_studio_base_url(),
            idempotency_key=idempotency_key,
        )
    except Conflict as exc:
        # Mark our reserve as expired so the partial-unique slot is
        # released. (``last_error_code`` doesn't exist on the model,
        # the previous assignment was a no-op kept only by the
        # ``update_fields`` skipping it; dropped now to avoid an
        # AttributeError if a future refactor saves the row unfiltered.)
        attempt.status = StudioCheckoutAttempt.Status.EXPIRED
        attempt.save(update_fields=["status", "updated_at"])

        # Extract the existing checkout URL from Intelligence's response
        # body and redirect there directly. Intelligence sets
        # ``details.checkout_url`` for ``open_checkout`` conflicts (and
        # ``details.stripe_session_id``), so we can route the user
        # straight back to the in-flight Stripe Checkout session
        # instead of bouncing them to a confusing "Another checkout is
        # in progress" warning.
        details = (exc.body or {}).get("details") or {}
        existing_url = details.get("checkout_url") if exc.code == "open_checkout" else None
        if existing_url:
            messages.info(
                request,
                "Resuming the checkout your teammate started for this org.",
            )
            return redirect(existing_url)
        # Anything else (already_active, pending_activation, in-progress
        # creating that hasn't promoted yet) falls back to the subscribe
        # page where the eligibility-cross-check we added above will
        # render the right resume / manage UI on the next render.
        messages.warning(
            request,
            "Couldn't start checkout: {}".format(exc.code or "conflict"),
        )
        return redirect("intelligence:subscribe", org_id=org_id)
    except (ServiceUnavailable, DeploymentNotAuthorized, IntelligenceClientError) as exc:
        attempt.delete()
        logger.exception("studio_checkout_session failed: %s", exc)
        messages.error(
            request,
            "We couldn't reach the billing service. Try again in a moment.",
        )
        return redirect("intelligence:subscribe", org_id=org_id)

    # ---- TX2: promote attempt to open + redirect -----------------------
    with transaction.atomic():
        attempt.stripe_session_id = resp["stripe_session_id"]
        attempt.checkout_url = resp["checkout_url"]
        attempt.status = StudioCheckoutAttempt.Status.OPEN
        if resp.get("expires_at"):
            with contextlib.suppress(ValueError, AttributeError):
                attempt.expires_at = datetime.fromisoformat(resp["expires_at"].replace("Z", "+00:00"))
        attempt.save(
            update_fields=[
                "stripe_session_id",
                "checkout_url",
                "status",
                "expires_at",
                "updated_at",
            ]
        )

    return redirect(resp["checkout_url"])


@require_POST
@require_org_permission("manage_intelligence_billing")
def discard_checkout(request, org_id):
    """Cancel an in-progress checkout attempt.

    Frees the partial-unique slot so the user can pick a different plan.
    Calls Intelligence ``/studio-checkout-session/cancel`` first so the
    authoritative remote row is closed (and the Stripe session expired)
    BEFORE the local mirror flips to canceled — otherwise the next
    ``/subscribe/`` render would still see ``open_checkout`` from the
    cross-check at ``subscribe()`` and resurrect the resume card.

    Three local-state shapes to handle:

    1. Local row in ``creating``/``open``/``pending`` — happy path.
       Cancel remote, flip local.
    2. No local row, Intelligence reports ``open_checkout`` via
       ``check_eligibility`` — drift case. Studio lost its mirror (a
       crash between Stripe.create and TX2 save, or an earlier discard
       that flipped local while Intelligence couldn't be reached). The
       subscribe view fabricates a resumable card from the remote
       response; the Discard button must be able to act on that too,
       otherwise the user is stuck staring at the card with no way out.
       Cancel remote, no local row to flip.
    3. Neither — nothing to discard.

    On Intelligence reachability failure we leave any local row
    untouched and surface an error message; reattempting later is safe
    because the cancel call is idempotent.
    """
    attempt = (
        StudioCheckoutAttempt.objects.filter(
            organization=request.org,
            status__in=[
                StudioCheckoutAttempt.Status.CREATING,
                StudioCheckoutAttempt.Status.OPEN,
                StudioCheckoutAttempt.Status.PENDING,
            ],
        )
        .order_by("-created_at")
        .first()
    )

    # Resolve the remote-only "drift" case: no local mirror but
    # Intelligence still reports open_checkout. Without this, the
    # subscribe view's cross-check keeps resurrecting the resume card
    # and the Discard button is a no-op.
    remote_session_id: str | None = None
    if attempt is None:
        try:
            remote = _client().check_eligibility(external_org_id=str(org_id))
        except (DeploymentNotAuthorized, IntelligenceClientError):
            messages.info(request, "No checkout to discard.")
            return redirect("intelligence:subscribe", org_id=org_id)
        if remote.get("reason") == "open_checkout":
            details = remote.get("details") or {}
            remote_session_id = details.get("stripe_session_id") or None
        if remote_session_id is None:
            # Nothing open anywhere.
            messages.info(request, "No checkout to discard.")
            return redirect("intelligence:subscribe", org_id=org_id)

    # Build the cancel call. Key the idempotency on the stable id of
    # what we're canceling — local UUID when we have one, else the
    # Stripe session id (which is the only stable id we know about the
    # remote-only attempt). Don't use ``request.org.id`` alone or
    # repeated discards across the lifetime of multiple checkouts
    # would all collide on the same idempotency slot.
    if attempt is not None:
        cancel_session_id = attempt.stripe_session_id or None
        idem_key = f"cancel-{attempt.id}"
    else:
        cancel_session_id = remote_session_id
        idem_key = f"cancel-remote-{remote_session_id}"

    try:
        _client().cancel_studio_checkout_session(
            external_org_id=str(request.org.id),
            stripe_session_id=cancel_session_id,
            idempotency_key=idem_key,
        )
    except Conflict:
        # Remote already terminal (activated/canceled). Local mirror is
        # the only thing left to reconcile.
        pass
    except (ServiceUnavailable, DeploymentNotAuthorized, IntelligenceClientError):
        logger.exception("cancel_studio_checkout_session failed")
        messages.error(
            request,
            "We couldn't reach the billing service. Try again in a moment.",
        )
        return redirect("intelligence:subscribe", org_id=org_id)

    # Flip local row if we have one; nothing to do in the remote-only case.
    if attempt is not None:
        with transaction.atomic():
            attempt.status = StudioCheckoutAttempt.Status.CANCELED
            attempt.consumed_at = timezone.now()
            attempt.save(update_fields=["status", "consumed_at", "updated_at"])

    messages.info(request, "Checkout discarded. Pick a plan to start a new one.")
    return redirect("intelligence:subscribe", org_id=org_id)


# ---------------------------------------------------------------------------
# Activate, Stripe success URL handler
# ---------------------------------------------------------------------------


@login_required
@require_GET
def activate(request):
    """Two-phase activation handler.

    1. Look up the local StudioCheckoutAttempt by session_id; if absent,
       this user did not initiate this session, reject.
    2. Re-check current OrgMembership of OWNER/ADMIN on the attempt's
       organization. Initiator identity is NOT trusted, only current
       role. (Defeats T18 demoted-admin bypass.)
    3. Call Intelligence /activate-preflight → returns validation_token.
    4. Re-check OrgMembership against ``resolved_external_org_id`` from
       the Intelligence response.
    5. Call Intelligence /activate-commit → returns api_key on first
       successful call, ``api_key_minted=False`` on replay.
    6. Store api_key (plaintext into EncryptedTextField). If
       ``api_key_minted=False`` and we have no local key, call rotate-key
       to recover.

    On transient failure between Phase 1 and Phase 2 (or between Phase 2
    and the local commit), persist PendingActivation + enqueue worker
    fallback + redirect to the finalizing page.
    """
    session_id = (request.GET.get("session_id") or "").strip()
    if not session_id:
        return HttpResponseBadRequest("session_id required")

    attempt = StudioCheckoutAttempt.objects.filter(
        stripe_session_id=session_id,
    ).first()
    if attempt is None:
        return render(
            request,
            "intelligence/activation_failed.html",
            {
                "code": "unknown_session",
                "message": "We don't recognize this Stripe session.",
                "organization": None,
            },
            status=400,
        )

    org = attempt.organization
    membership = OrgMembership.objects.filter(
        user=request.user,
        organization=org,
        org_role__in=[OrgMembership.OrgRole.OWNER, OrgMembership.OrgRole.ADMIN],
    ).first()
    if membership is None:
        return render(
            request,
            "intelligence/activation_org_mismatch.html",
            {
                "organization": org,
            },
            status=403,
        )

    try:
        return _activate_two_phase(
            request,
            session_id=session_id,
            attempt=attempt,
            expected_org=org,
            user=request.user,
        )
    except _DeferredToWorker:
        # Fallback path, PendingActivation already persisted in
        # ``_activate_two_phase``. Send the user to the finalizing page.
        return redirect("intelligence_global:finalizing")


class _DeferredToWorker(Exception):
    """Internal signal that activation has been queued for the worker."""


def _activate_two_phase(request, *, session_id, attempt, expected_org, user):
    """Two-phase + lost-key rotation. May raise ``_DeferredToWorker`` to
    signal a worker fallback."""
    preflight_key = f"preflight-{session_id}"
    try:
        preflight = _client().activate_preflight(
            session_id=session_id,
            expected_external_org_id=str(expected_org.id),
            plan_slug=attempt.plan_slug,
            billing_email=expected_org.billing_email or "",
            org_name=expected_org.name,
            contact_email=user.email,
            contact_full_name=user.name or "",
            idempotency_key=preflight_key,
        )
    except ActivationRejected as exc:
        logger.warning("Activation preflight rejected: code=%s", exc.code)
        return render(
            request,
            "intelligence/activation_failed.html",
            {
                "code": exc.code,
                "message": exc.user_message,
                "organization": expected_org,
            },
            status=exc.status_code or 400,
        )
    except ServiceUnavailable:
        # 5xx / network error — genuinely transient, defer to worker.
        logger.exception("Preflight transient failure; deferring to worker")
        _queue_pending_activation(user, session_id)
        # ``_DeferredToWorker`` is a flow-control signal, not an error
        # — the user-facing failure is the worker-fallback redirect we're
        # about to do. Drop the chain explicitly so the traceback in
        # logs/Sentry doesn't show the upstream ServiceUnavailable
        # underneath the signal exception.
        raise _DeferredToWorker from None
    except IntelligenceClientError as exc:
        # Any other 4xx — bad request, conflict, etc. These are permanent
        # for the same payload; the worker would just spin on them. Surface
        # to the user instead of pretending to "finalize" forever.
        logger.error(
            "Preflight permanent client error: code=%s status=%s body=%s",
            getattr(exc, "code", None),
            getattr(exc, "status_code", None),
            getattr(exc, "body", None),
        )
        return render(
            request,
            "intelligence/activation_failed.html",
            {
                "code": getattr(exc, "code", "") or "preflight_failed",
                "message": (
                    "We couldn't complete activation. Please refresh and try "
                    "again, or contact support if this persists."
                ),
                "organization": expected_org,
            },
            status=getattr(exc, "status_code", 400) or 400,
        )

    resolved_org_id = preflight.get("resolved_external_org_id")
    if str(expected_org.id) != str(resolved_org_id):
        # Intelligence resolved a different org than ours. Refuse to commit.
        return render(
            request,
            "intelligence/activation_org_mismatch.html",
            {
                "organization": expected_org,
            },
            status=403,
        )

    # Re-check membership against the resolved org (belt-and-braces; should
    # be identical to expected_org but the plan calls for the explicit
    # second check).
    membership = OrgMembership.objects.filter(
        user=user,
        organization_id=resolved_org_id,
        org_role__in=[OrgMembership.OrgRole.OWNER, OrgMembership.OrgRole.ADMIN],
    ).first()
    if membership is None:
        return render(
            request,
            "intelligence/activation_org_mismatch.html",
            {
                "organization": expected_org,
            },
            status=403,
        )

    commit_key = f"commit-{session_id}"
    try:
        commit_resp = _client().activate_commit(
            validation_token=preflight["validation_token"],
            contact_email=user.email,
            contact_full_name=user.name or "",
            billing_email=expected_org.billing_email or "",
            org_name=expected_org.name,
            idempotency_key=commit_key,
        )
    except ActivationRejected as exc:
        return render(
            request,
            "intelligence/activation_failed.html",
            {
                "code": exc.code,
                "message": exc.user_message,
                "organization": expected_org,
            },
            status=exc.status_code or 400,
        )
    except ServiceUnavailable:
        # 5xx / network error — genuinely transient, defer to worker.
        logger.exception("Commit transient failure; deferring to worker")
        _queue_pending_activation(user, session_id)
        # ``_DeferredToWorker`` is a flow-control signal, not an error
        # — the user-facing failure is the worker-fallback redirect we're
        # about to do. Drop the chain explicitly so the traceback in
        # logs/Sentry doesn't show the upstream ServiceUnavailable
        # underneath the signal exception.
        raise _DeferredToWorker from None
    except IntelligenceClientError as exc:
        # 4xx — permanent for the same payload; surface to the user
        # instead of spinning the worker.
        logger.error(
            "Commit permanent client error: code=%s status=%s body=%s",
            getattr(exc, "code", None),
            getattr(exc, "status_code", None),
            getattr(exc, "body", None),
        )
        return render(
            request,
            "intelligence/activation_failed.html",
            {
                "code": getattr(exc, "code", "") or "commit_failed",
                "message": (
                    "We couldn't complete activation. Please refresh and try "
                    "again, or contact support if this persists."
                ),
                "organization": expected_org,
            },
            status=getattr(exc, "status_code", 400) or 400,
        )

    # Final local commit. Wrap in the same transient handler as the
    # phase calls above so a rotate-key failure during lost-key recovery
    # also defers to the worker rather than escaping as 500 (and rather
    # than marking the sub ACTIVE without an api_key, see the lost-key
    # branch in ``_finalize_local_subscription``).
    try:
        return _finalize_local_subscription(
            request,
            attempt=attempt,
            expected_org=expected_org,
            commit_resp=commit_resp,
        )
    except (ServiceUnavailable, IntelligenceClientError):
        logger.exception("Finalize transient failure; deferring to worker")
        _queue_pending_activation(user, session_id)
        # ``_DeferredToWorker`` is a flow-control signal, not an error
        # — the user-facing failure is the worker-fallback redirect we're
        # about to do. Drop the chain explicitly so the traceback in
        # logs/Sentry doesn't show the upstream ServiceUnavailable
        # underneath the signal exception.
        raise _DeferredToWorker from None


def _queue_pending_activation(user, session_id: str):
    """Persist PendingActivation + enqueue worker."""
    from .tasks import provision_intelligence_account_via_session

    pending, _ = PendingActivation.objects.update_or_create(
        user=user,
        session_id=session_id,
        defaults={"status": PendingActivation.Status.PENDING},
    )
    # ``pending.id`` is a UUID; django-background-tasks JSON-encodes
    # task args, and UUID is not JSON-serializable. Pass the string form
    # to avoid a "Object of type UUID is not JSON serializable" 500.
    provision_intelligence_account_via_session(str(pending.id), schedule=0)


def _finalize_local_subscription(request, *, attempt, expected_org, commit_resp):
    """Write the IntelligenceSubscription row + redirect.

    Handles the api_key_minted=False replay case by calling /rotate-key
    if the local row has no key yet (would happen if Studio crashed
    between a previous commit's HTTP response and the local save).
    """
    api_key = commit_resp.get("api_key")
    api_key_minted = commit_resp.get("api_key_minted", False)

    with transaction.atomic():
        sub, _ = IntelligenceSubscription.objects.select_for_update().get_or_create(
            organization=expected_org,
            defaults={"status": IntelligenceSubscription.Status.PROVISIONING},
        )
        if api_key_minted and api_key:
            sub.intelligence_api_key = api_key
            sub.intelligence_api_key_prefix = api_key[:8]
        elif not sub.intelligence_api_key:
            # Lost-key recovery: server cached the response but we don't
            # have the plaintext. Rotate.
            #
            # If rotation fails, we MUST NOT mark the sub ACTIVE, an
            # active sub with no api_key produces an unusable state
            # (every tool call hits ``IntelligenceAPIClient(api_key="")``
            # and raises ValueError, which escapes the typed
            # IntelligenceClientError path in ``_call_tool``). Raise so
            # the caller defers to the worker, which re-enters the same
            # flow and tries rotation again with exponential backoff.
            try:
                rot = _client().rotate_key(
                    user_id=commit_resp["user_id"],
                    external_org_id=str(expected_org.id),
                    idempotency_key=f"rotate-{expected_org.id}-{int(time.time())}",
                )
            except IntelligenceClientError:
                logger.exception(
                    "rotate-key fallback failed; deferring to worker rather than activating without an api_key",
                )
                raise
            sub.intelligence_api_key = rot["api_key"]
            sub.intelligence_api_key_prefix = rot["api_key"][:8]

        sub.intelligence_account_id = str(commit_resp.get("user_id") or "")
        sub.plan_slug = commit_resp.get("plan_slug", "")
        if commit_resp.get("period_end"):
            with contextlib.suppress(ValueError, AttributeError):
                sub.current_period_end = datetime.fromisoformat(
                    commit_resp["period_end"].replace("Z", "+00:00"),
                )
        sub.status = IntelligenceSubscription.Status.ACTIVE
        sub.last_synced_at = timezone.now()
        sub.save()

        attempt.status = StudioCheckoutAttempt.Status.ACTIVATED
        attempt.consumed_at = timezone.now()
        attempt.save(update_fields=["status", "consumed_at", "updated_at"])

    return redirect("intelligence:playground", org_id=expected_org.id)


# ---------------------------------------------------------------------------
# Recover (closed-tab)
# ---------------------------------------------------------------------------


@require_POST
@require_org_permission("manage_intelligence_billing")
def recover(request, org_id):
    """Closed-tab recovery flow.

    Studio's playground discovers a webhook-persisted Pending row via
    ``/internal/v1/pending-activation``; this view runs the two-phase
    activation against that row's ``session_id``."""
    pending = _client().pending_activation(external_org_id=str(org_id))
    if pending is None:
        messages.warning(request, "No pending activation found.")
        return redirect("intelligence:playground", org_id=org_id)

    session_id = pending["stripe_session_id"]
    # Intelligence resolves plan_slug server-side (from the price_id on
    # the pending row) so closed-tab recovery doesn't have to. Falls
    # back to "" if Intel returned an older response shape, preflight
    # accepts blank and re-resolves from the same price_id, so the
    # activation still completes either way.
    plan_slug = (pending.get("plan_slug") or "").strip()
    # Fabricate a local attempt row so the two-phase logic finds it.
    # NOTE: ``update_or_create(organization=...)`` would raise
    # MultipleObjectsReturned for any org with checkout history,
    # StudioCheckoutAttempt's partial-unique index only covers
    # creating|open|pending, so terminal rows accumulate. Look up by
    # (organization, stripe_session_id) instead (Stripe session ids are
    # globally unique), then fall back to a fresh create with a
    # defensive sweep of any non-terminal row that would conflict with
    # the partial-unique index.
    attempt = StudioCheckoutAttempt.objects.filter(
        organization=request.org,
        stripe_session_id=session_id,
    ).first()
    open_defaults = {
        "user": request.user,
        "plan_slug": plan_slug,
        "billing_email": request.org.billing_email or request.user.email,
        "status": StudioCheckoutAttempt.Status.OPEN,
        "checkout_url": "",
        "idempotency_key": f"recover-{request.org.id}",
    }
    if attempt is not None:
        for field, value in open_defaults.items():
            setattr(attempt, field, value)
        attempt.save(update_fields=list(open_defaults) + ["updated_at"])
    else:
        with transaction.atomic():
            # An unrelated non-terminal attempt (e.g. an abandoned
            # ``creating`` row from a previous failed checkout) would
            # collide with the partial-unique index. Expire it so this
            # recovery can proceed; audit trail preserved via the row,
            # not deleted.
            StudioCheckoutAttempt.objects.filter(
                organization=request.org,
                status__in=[
                    StudioCheckoutAttempt.Status.CREATING,
                    StudioCheckoutAttempt.Status.OPEN,
                    StudioCheckoutAttempt.Status.PENDING,
                ],
            ).update(
                status=StudioCheckoutAttempt.Status.EXPIRED,
                consumed_at=timezone.now(),
            )
            attempt = StudioCheckoutAttempt.objects.create(
                organization=request.org,
                stripe_session_id=session_id,
                **open_defaults,
            )
    try:
        return _activate_two_phase(
            request,
            session_id=session_id,
            attempt=attempt,
            expected_org=request.org,
            user=request.user,
        )
    except _DeferredToWorker:
        return redirect("intelligence_global:finalizing")


# ---------------------------------------------------------------------------
# Polling endpoints (status / finalizing)
# ---------------------------------------------------------------------------


@require_GET
@require_org_permission("use_intelligence")
def status_fragment(request, org_id):
    """HTMX polling fragment for the playground overlay. Returns 204 when
    nothing has changed (HTMX leaves the existing partial in place);
    returns an OOB swap fragment when the state transitions to active."""
    sub = getattr(request.org, "intelligence_subscription", None)
    if sub is None:
        return HttpResponse(status=204)
    if sub.status == IntelligenceSubscription.Status.ACTIVE:
        return render(
            request,
            "intelligence/_status_active_oob.html",
            {"organization": request.org, "subscription": sub},
        )
    return render(
        request,
        "intelligence/_status_polling.html",
        {"organization": request.org, "subscription": sub},
    )


@login_required
@require_GET
def finalizing(request):
    """User-scoped finalizing page shown when sync activation transient-failed
    before we could resolve an org. Polls the user-scoped fragment below."""
    pending = PendingActivation.objects.filter(user=request.user).order_by("-created_at").first()
    return render(
        request,
        "intelligence/finalizing.html",
        {"pending": pending},
    )


@login_required
@require_GET
def finalizing_status(request):
    """HTMX polling fragment for the user-scoped finalizing page."""
    pending = PendingActivation.objects.filter(user=request.user).order_by("-created_at").first()
    if pending is None:
        return HttpResponse(status=204)
    if pending.status == PendingActivation.Status.COMPLETED and pending.resolved_organization_id:
        return render(
            request,
            "intelligence/_finalizing_completed.html",
            {"org_id": pending.resolved_organization_id},
        )
    if pending.status == PendingActivation.Status.REJECTED_UNAUTHORIZED:
        return render(
            request,
            "intelligence/_finalizing_unauthorized.html",
            {},
        )
    if pending.status == PendingActivation.Status.PROVISIONING_FAILED:
        return render(
            request,
            "intelligence/_finalizing_failed.html",
            {"last_error": pending.last_error},
        )
    return render(
        request,
        "intelligence/_finalizing_polling.html",
        {"pending": pending},
    )


# ---------------------------------------------------------------------------
# Billing management
# ---------------------------------------------------------------------------


@require_POST
@require_org_permission("manage_intelligence_billing")
def portal(request, org_id):
    """Mint a Stripe Customer Portal URL via Intelligence + 302."""
    try:
        resp = _client().portal_session(external_org_id=str(org_id))
    except (ServiceUnavailable, IntelligenceClientError) as exc:
        logger.exception("portal_session failed: %s", exc)
        messages.error(
            request,
            "We couldn't open the billing portal. Try again in a moment.",
        )
        return redirect("intelligence:playground", org_id=org_id)
    return redirect(resp["url"])


@require_GET
@require_org_permission("manage_intelligence_billing")
def billing_settings(request, org_id):
    sub = getattr(request.org, "intelligence_subscription", None)
    # Fresh "scheduled cancel" lookup. Stripe keeps status='active' until
    # the period actually ends, so the local IntelligenceSubscription.status
    # cannot answer "is this sub going to cancel?", that lives in
    # Stripe's ``cancel_at`` / ``cancel_at_period_end`` fields. Intel
    # proxies them through /internal/v1/accounts/<user_id> by retrieving
    # the live Stripe object server-side. Failure to reach Intel here is
    # non-fatal, we just skip the "Will cancel on …" banner and let the
    # status pill speak for itself.
    account = None
    if sub and sub.intelligence_account_id:
        try:
            account = _client().get_account(user_id=sub.intelligence_account_id)
        except (ServiceUnavailable, IntelligenceClientError):
            logger.warning(
                "Failed to load /accounts/%s for billing page; rendering without cancel info",
                sub.intelligence_account_id,
            )

    cancel_at = None
    if account and account.get("cancel_at"):
        try:
            cancel_at = datetime.fromisoformat(
                account["cancel_at"].replace("Z", "+00:00"),
            )
        except (ValueError, AttributeError):
            cancel_at = None
    canceled_at = None
    if account and account.get("canceled_at"):
        try:
            canceled_at = datetime.fromisoformat(
                account["canceled_at"].replace("Z", "+00:00"),
            )
        except (ValueError, AttributeError):
            canceled_at = None

    return render(
        request,
        "intelligence/billing_settings.html",
        {
            "organization": request.org,
            "subscription": sub,
            "billing_email": request.org.billing_email or request.user.email,
            # Stripe-level scheduled-cancel state, may be None if Intel was
            # unreachable or the sub has no scheduled cancel.
            "cancel_at": cancel_at,
            "canceled_at": canceled_at,
            "cancel_at_period_end": bool(account and account.get("cancel_at_period_end")),
        },
    )


@require_POST
@require_org_permission("manage_intelligence_billing")
def update_billing_contact(request, org_id):
    billing_email = (request.POST.get("billing_email") or "").strip()
    if not billing_email:
        return HttpResponseBadRequest("billing_email required")

    # When an active subscription exists we MUST keep Studio and the
    # billing service in sync, the previous order (save locally, then
    # call Intelligence) silently diverged whenever the Intel call
    # failed: there's no Studio-side retry queue, so the "It'll retry
    # automatically" message was a lie and Stripe/Studio could drift
    # permanently. Call Intel first; only persist locally once Intel
    # acknowledges. If Intel is down, surface the failure and ask the
    # user to retry rather than half-committing.
    sub = getattr(request.org, "intelligence_subscription", None)
    if sub is not None and sub.status == IntelligenceSubscription.Status.ACTIVE:
        try:
            _client().update_billing_contact(
                external_org_id=str(org_id),
                billing_email=billing_email,
                org_name=request.org.name,
            )
        except (ServiceUnavailable, IntelligenceClientError):
            logger.exception("update_billing_contact sync failed")
            messages.error(
                request,
                "We couldn't reach the billing service. Your change has NOT been saved, please try again in a moment.",
            )
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "intelligence/_billing_contact_saved.html",
                    {"billing_email": request.org.billing_email, "error": True},
                )
            return redirect("intelligence:billing-settings", org_id=org_id)

    with transaction.atomic():
        request.org.billing_email = billing_email
        request.org.save(update_fields=["billing_email", "updated_at"])

    if request.headers.get("HX-Request"):
        return render(
            request,
            "intelligence/_billing_contact_saved.html",
            {"billing_email": billing_email},
        )
    messages.success(request, "Billing contact updated.")
    return redirect("intelligence:billing-settings", org_id=org_id)


# ---------------------------------------------------------------------------
# Tool endpoints, six HTMX POSTs
# ---------------------------------------------------------------------------


def _call_tool(request, method_name: str, *, body: dict, template: str, endpoint_path: str):
    """Shared tool-call shim: dispatch to the per-org IntelligenceAPIClient
    method, render the result partial, and log a usage event."""
    sub = request.org.intelligence_subscription
    api = _api_client_for(sub)
    start = time.monotonic()
    try:
        result = getattr(api, method_name)(**body)
    except IntelligenceClientError as exc:
        latency = int((time.monotonic() - start) * 1000)
        _record_usage(
            organization=request.org,
            user=request.user,
            endpoint=endpoint_path,
            status_code=exc.status_code or 500,
            latency_ms=latency,
        )
        return _render_tool_error(request, exc, organization=request.org)

    latency = int((time.monotonic() - start) * 1000)
    _record_usage(
        organization=request.org,
        user=request.user,
        endpoint=endpoint_path,
        status_code=200,
        latency_ms=latency,
        credits_charged=_credits_for(endpoint_path),
    )
    return render(
        request,
        template,
        {
            "result": result,
            "organization": request.org,
        },
    )


def _credits_for(endpoint_path: str) -> int:
    """Mirror of Intelligence's per-endpoint credit cost (display-only,
    Intelligence is authoritative)."""
    return {
        "/v1/score/packaging": 1,
        "/v1/score/video-hook": 10,
        "/v1/benchmark/channel": 5,
        "/v1/benchmark/video": 3,
        "/v1/research/content-gaps": 5,
        "/v1/research/niches": 1,
    }.get(endpoint_path, 0)


SCORE_PACKAGING_MAX_THUMBNAIL_BYTES = 5 * 1024 * 1024  # 5 MiB
SCORE_PACKAGING_ALLOWED_THUMBNAIL_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)
# Pillow returns these for the same MIME types; both axes (browser-reported
# content_type AND Pillow-detected format) must match the allow-list before
# we forward bytes to Intelligence.
SCORE_PACKAGING_ALLOWED_PIL_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


def _validate_thumbnail_upload(uploaded):
    """Reject any uploaded file that isn't a real, small image.

    Returns (base64_string, None) on success; (None, error_message) on
    rejection. Defends against:

    - Oversized payloads (size cap before Pillow even touches the file).
    - MIME spoofing (browser ``content_type`` is user-controlled; we
      cross-check against Pillow's magic-byte format detection).
    - Polyglot files / HTML-as-image / corrupted images (Pillow
      ``verify()`` rejects anything it can't parse as a real image).
    - Extension-only forgery (we don't trust the filename at all).
    """
    import base64
    import io

    from PIL import Image, UnidentifiedImageError

    if uploaded.size > SCORE_PACKAGING_MAX_THUMBNAIL_BYTES:
        return None, "Thumbnail must be 5 MB or smaller."

    # Browser-reported content-type is the first cheap filter. It's
    # NOT trusted on its own, a malicious client can send any string,
    # but it filters out the obvious noise before we spend Pillow cycles.
    content_type = (uploaded.content_type or "").lower()
    if content_type not in SCORE_PACKAGING_ALLOWED_THUMBNAIL_TYPES:
        return None, "Thumbnail must be a JPEG, PNG, or WebP image."

    # Read once into memory. Capped to 5 MB above, so memory is bounded.
    raw = uploaded.read()
    if len(raw) > SCORE_PACKAGING_MAX_THUMBNAIL_BYTES:
        # Defensive: ``uploaded.size`` is the multipart parser's view;
        # actual read length can differ in pathological cases.
        return None, "Thumbnail must be 5 MB or smaller."

    # Pillow magic-byte check. ``verify()`` parses the header + does a
    # cheap structural sanity pass without decoding the full image, then
    # we use ``Image.open`` a second time to read ``format`` (the first
    # Image is unusable after verify() per Pillow docs).
    try:
        Image.open(io.BytesIO(raw)).verify()
        pil_format = Image.open(io.BytesIO(raw)).format
    except (UnidentifiedImageError, OSError, ValueError):
        return None, "Thumbnail is not a recognized image file."

    if pil_format not in SCORE_PACKAGING_ALLOWED_PIL_FORMATS:
        return None, "Thumbnail must be a JPEG, PNG, or WebP image."

    return base64.b64encode(raw).decode("ascii"), None


@require_POST
@require_org_permission("use_intelligence")
@intelligence_subscription_required
def score_packaging(request, org_id):
    title = (request.POST.get("title") or "").strip() or None

    # Thumbnail: accept ONLY a multipart file upload, we deliberately
    # do NOT accept ``thumbnail_url`` or a client-supplied
    # ``thumbnail_base64`` POST field. Removing URL support eliminates
    # an SSRF surface (server-side URL fetches against attacker-chosen
    # hosts), and refusing client-base64 forces the file through the
    # validation pipeline above so a malicious client can't smuggle
    # non-image bytes by setting a fake data-URL prefix.
    thumbnail_base64 = None
    uploaded = request.FILES.get("thumbnail")
    if uploaded is not None:
        thumbnail_base64, err = _validate_thumbnail_upload(uploaded)
        if err is not None:
            return render(
                request,
                "intelligence/_tool_error.html",
                {"code": "invalid_thumbnail", "message": err, "organization": request.org},
                status=400,
            )

    if not title and not thumbnail_base64:
        return render(
            request,
            "intelligence/_tool_error.html",
            {"code": "missing_input", "message": "Provide a title, a thumbnail, or both.", "organization": request.org},
            status=400,
        )

    body: dict = {}
    if title is not None:
        body["title"] = title
    if thumbnail_base64 is not None:
        body["thumbnail_base64"] = thumbnail_base64

    return _call_tool(
        request,
        "score_packaging",
        body=body,
        template="intelligence/_score_packaging_result.html",
        endpoint_path="/v1/score/packaging",
    )


@require_POST
@require_org_permission("use_intelligence")
@intelligence_subscription_required
def score_video_hook(request, org_id):
    body = {"youtube_url": request.POST.get("youtube_url", "").strip()}
    return _call_tool(
        request,
        "score_video_hook",
        body=body,
        template="intelligence/_score_video_hook_result.html",
        endpoint_path="/v1/score/video-hook",
    )


@require_POST
@require_org_permission("use_intelligence")
@intelligence_subscription_required
def benchmark_channel(request, org_id):
    body = {"url": request.POST.get("url", "").strip()}
    return _call_tool(
        request,
        "benchmark_channel",
        body=body,
        template="intelligence/_benchmark_channel_result.html",
        endpoint_path="/v1/benchmark/channel",
    )


@require_POST
@require_org_permission("use_intelligence")
@intelligence_subscription_required
def benchmark_video(request, org_id):
    body = {"url": request.POST.get("url", "").strip()}
    return _call_tool(
        request,
        "benchmark_video",
        body=body,
        template="intelligence/_benchmark_video_result.html",
        endpoint_path="/v1/benchmark/video",
    )


@require_POST
@require_org_permission("use_intelligence")
@intelligence_subscription_required
def research_content_gaps(request, org_id):
    niche = (request.POST.get("niche") or "").strip()
    if not niche:
        return HttpResponseBadRequest("niche required")
    try:
        limit = int(request.POST.get("limit") or 20)
        min_score = int(request.POST.get("min_score") or 0)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("limit and min_score must be integers")
    body = {
        "niche": niche,
        "limit": limit,
        "min_score": min_score,
    }
    gap_type = request.POST.getlist("gap_type") if hasattr(request.POST, "getlist") else None
    if gap_type:
        body["gap_type"] = gap_type
    return _call_tool(
        request,
        "research_content_gaps",
        body=body,
        template="intelligence/_research_content_gaps_result.html",
        endpoint_path="/v1/research/content-gaps",
    )


@require_POST
@require_org_permission("use_intelligence")
@intelligence_subscription_required
def list_niches(request, org_id):
    return _call_tool(
        request,
        "list_niches",
        body={},
        template="intelligence/_list_niches_result.html",
        endpoint_path="/v1/research/niches",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _studio_base_url() -> str:
    """The publicly-reachable base URL for THIS Studio deployment.

    Intelligence validates ``return_base_url`` against the registered
    ``StudioDeployment.base_url`` and refuses if they differ, open-
    redirect defense, so we send whatever is configured in env.
    """
    from django.conf import settings

    return getattr(settings, "STUDIO_BASE_URL", "").rstrip("/")
