"""Cross-cutting helpers the routers reach for: audit log + idempotency.

Not Django middleware in the technical sense — these are small synchronous
helpers each route calls directly. We avoid a real Django middleware
because Ninja's auth runs *after* Django middleware, so an audit-log
middleware would have no API key to attach to until the route body had
already run.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from django.http import HttpRequest

from apps.api.models import IdempotencyRecord
from apps.api_keys.models import ApiKey, ApiKeyAuditLog

# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def log_audit_entry(
    request: HttpRequest,
    *,
    action: str,
    target_id: uuid.UUID | None,
    status_code: int,
) -> None:
    """Persist one ``ApiKeyAuditLog`` row for the request.

    Deliberately omits request body — payloads may contain media URLs
    with embedded signed tokens. We record verb + resource ID + outcome,
    which is enough for "who did what when" without paying the privacy
    cost of full bodies.

    Best-effort: a failure to write the audit row must NOT fail the
    parent request. The agent shouldn't see "publish succeeded but
    audit logging failed" as a 500.
    """
    api_key: ApiKey | None = getattr(request, "api_key", None)
    if api_key is None:
        # Anonymous (failed-auth) paths produce no audit row — they're
        # represented by the rate-limit counter on the IP throttle.
        return
    # OAuth MCP callers carry an ``OAuthMcpActor`` shim (not a saved ApiKey),
    # so we attribute the row to the user via ``actor_user`` instead of the
    # ``api_key`` FK. See apps/api/auth.py::OAuthMcpActor.
    is_oauth = getattr(api_key, "is_oauth", False)
    try:
        ApiKeyAuditLog.objects.create(
            api_key=None if is_oauth else api_key,
            actor_user=api_key.issued_by if is_oauth else None,
            actor_label="oauth" if is_oauth else "",
            action=action,
            target_id=target_id,
            method=request.method or "",
            path=request.path[:255],
            status_code=status_code,
            ip=_client_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:512],
        )
    except Exception:  # noqa: BLE001 — best-effort, swallow.
        import logging

        logging.getLogger(__name__).warning(
            "Failed to write ApiKeyAuditLog for actor %s", getattr(api_key, "id", "oauth"), exc_info=True
        )


def _client_ip(request: HttpRequest) -> str | None:
    """Delegate to the canonical, proxy-trust-aware implementation.

    Originally a duplicate of the same logic in ``apps/api/limits.py`` —
    deliberately collapsed so the trust policy (``BB_TRUSTED_PROXIES``)
    lives in exactly one place. The two call sites (audit log and
    throttle) MUST agree on the IP they record vs throttle; a divergence
    would let one tier honour a spoofed XFF the other ignored.
    """
    from apps.api.limits import _client_ip as _canonical

    return _canonical(request)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------
#
# We use an "atomic claim" pattern, not a read-then-write check, so two
# concurrent identical POSTs cannot both miss the lookup and then both
# create the underlying resource. The flow is:
#
#   1. Try to INSERT a placeholder row with ``response_status = 0``
#      (HTTP never uses 0, so it's a safe sentinel for "in-flight").
#   2. INSERT raises ``IntegrityError`` on the unique constraint
#      ``(api_key, key)`` — that's our atomic mutex. If we got the
#      IntegrityError, fetch the existing row and decide:
#        - fingerprint mismatch → 422
#        - status == 0 (peer still mid-flight) → 409 "in progress"
#        - status > 0 → replay verbatim
#   3. If we own the slot, do the work in a try / except. On success,
#      ``update()`` the row with the real response. On failure, DELETE
#      the placeholder so the agent's next retry can succeed.
#
# This is the same pattern Stripe documents for its Idempotency-Key
# header. It costs one extra DB round-trip per fresh request but the
# trade is correctness under concurrency.

#: Sentinel value stored in ``response_status`` to mean "another worker
#: holds this idempotency slot but hasn't filled in the real response
#: yet." We pick 0 because HTTP status codes start at 100, so there's
#: no ambiguity with a real response.
PENDING_STATUS_SENTINEL = 0


def fingerprint_request(method: str, path: str, body: dict[str, Any]) -> str:
    """Stable hash of (method, path, canonical-JSON body).

    Used to detect "client reused the idempotency key for a different
    intent". We hash a sorted, separator-tight JSON dump so the order
    of keys in the incoming JSON doesn't affect the fingerprint.
    """
    canonical = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        default=str,  # uuid/datetime → str
    )
    return hashlib.sha256(f"{method}\n{path}\n{canonical}".encode()).hexdigest()


def claim_idempotency_slot(
    *,
    api_key: ApiKey,
    idempotency_key: str | None,
    fingerprint: str,
) -> tuple[str, int | None, dict[str, Any] | None]:
    """Atomic gate at the front of every idempotent POST.

    Returns a tuple ``(disposition, status, body)`` where ``disposition``
    is one of:

    * ``"passthrough"`` — caller did not pass an idempotency key; proceed
      with no caching and skip ``finalize_idempotent_response`` later.
    * ``"claimed"`` — this caller owns the slot. Proceed to do the work.
      MUST call ``finalize_idempotent_response`` on success or
      ``release_idempotent_claim`` on failure, otherwise future retries
      will see an "in-progress" claim until the 24h sweep
      (``apps.api.tasks.sweep_stale_idempotency_records``) deletes it.
    * ``"replay"`` — a prior request with this key + matching fingerprint
      already completed. Return ``(status, body)`` to the client verbatim.
    * ``"in_flight"`` — another worker is mid-flight on this same key;
      caller should respond with 409 and ask the client to retry.

    Raises ``ValueError`` when the key was reused with a different body
    (caller turns this into 422).
    """
    from django.db import IntegrityError, transaction

    if not idempotency_key:
        return "passthrough", None, None

    try:
        with transaction.atomic():
            IdempotencyRecord.objects.create(
                api_key=api_key,
                key=idempotency_key,
                request_fingerprint=fingerprint,
                response_status=PENDING_STATUS_SENTINEL,
                response_body={},
            )
        return "claimed", None, None
    except IntegrityError:
        # Lost the race — another worker either finished (replay) or is
        # still in flight (409). Re-fetch the now-existing row.
        existing = IdempotencyRecord.objects.get(api_key=api_key, key=idempotency_key)
        if existing.request_fingerprint != fingerprint:
            raise ValueError(
                "idempotency_key reused with a different request body — "
                "either change the key or send the original body."
            ) from None
        if existing.response_status == PENDING_STATUS_SENTINEL:
            return "in_flight", None, None
        return "replay", existing.response_status, existing.response_body


def finalize_idempotent_response(
    *,
    api_key: ApiKey,
    idempotency_key: str | None,
    status_code: int,
    body: dict[str, Any],
) -> None:
    """Promote a claimed slot to its real response.

    No-op when the caller didn't pass a key. Uses ``filter().update()``
    rather than ``save()`` to avoid clobbering ``fingerprint`` (we want
    the fingerprint set at claim time to remain the canonical one).
    """
    if not idempotency_key:
        return
    IdempotencyRecord.objects.filter(api_key=api_key, key=idempotency_key).update(
        response_status=status_code,
        response_body=body,
    )


def release_idempotent_claim(
    *,
    api_key: ApiKey,
    idempotency_key: str | None,
) -> None:
    """Delete a claimed-but-not-finalized slot so retries can succeed.

    Call this on the error path inside the route when ``create_post``
    or any later step raises. Otherwise an internal failure would leave
    a phantom "in-flight" record around for 24h and the agent's retry
    would 409 indefinitely.
    """
    if not idempotency_key:
        return
    IdempotencyRecord.objects.filter(
        api_key=api_key,
        key=idempotency_key,
        response_status=PENDING_STATUS_SENTINEL,
    ).delete()
