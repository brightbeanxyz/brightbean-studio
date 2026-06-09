"""Two-layer Intelligence client.

``InternalClient`` talks to Intelligence's HMAC-signed /internal/v1/
endpoints (provisioning, eligibility, billing, etc.). Every mutating
call carries an idempotency key + a fresh nonce; the canonical signing
string binds method + path + timestamp + body hash + deployment id +
nonce so a captured request cannot be replayed across endpoints,
methods, or deployments.

``IntelligenceAPIClient`` talks to Intelligence's public /v1/ tool
endpoints using a per-org bearer ``bb_`` key. This is the layer Studio
view code calls to score packaging, benchmark channels, etc.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any

import httpx
from django.conf import settings

from .exceptions import (
    ActivationRejected,
    BadRequest,
    Conflict,
    DeploymentNotAuthorized,
    InsufficientCredits,
    IntelligenceClientError,
    InvalidApiKey,
    NotFound,
    RateLimited,
    ServiceUnavailable,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# InternalClient, HMAC + nonce + idempotency
# ---------------------------------------------------------------------------


_ACTIVATION_REJECTED_CODES = frozenset(
    {
        "metadata_missing_studio_source",
        "deployment_mismatch",
        "client_reference_mismatch",
        "price_not_allowlisted",
        "not_paid",
        "session_not_found",
        "session_incomplete",
        "wrong_mode",
        "no_line_items",
        "unknown_checkout_attempt",
        "token_expired",
        "token_already_consumed",
        "invalid_token",
        "token_deployment_mismatch",
        "missing_subscription_id",
        "unknown_plan",
        "unmapped_price",
        "no_pending_activation",
        "session_id_mismatch",
    }
)


class InternalClient:
    """HMAC-signed client for Intelligence's /internal/v1/.

    Construct without arguments, pulls config from Django settings.
    Methods raise typed exceptions on HTTP errors so the view layer can
    pattern-match without inspecting status codes.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        deployment_id: str | None = None,
        secret: str | None = None,
        timeout: float = 8.0,
    ):
        self.base_url = (base_url or settings.INTELLIGENCE_INTERNAL_URL).rstrip("/")
        self.deployment_id = deployment_id or settings.STUDIO_DEPLOYMENT_ID
        self.secret = secret or settings.STUDIO_SHARED_SECRET
        self.timeout = timeout

    # ---- Plan / eligibility / pending-activation (GET) -------------------

    def list_plans(self) -> dict:
        return self._request("GET", "/plans")

    def check_eligibility(self, *, external_org_id: str) -> dict:
        return self._request(
            "GET",
            "/check-eligibility",
            query={"external_org_id": external_org_id},
        )

    def pending_activation(self, *, external_org_id: str) -> dict | None:
        try:
            return self._request(
                "GET",
                "/pending-activation",
                query={"external_org_id": external_org_id},
            )
        except NotFound:
            return None

    # ---- Activation (POST, idempotent) -----------------------------------

    def studio_checkout_session(
        self,
        *,
        external_org_id: str,
        org_name: str,
        billing_email: str,
        plan_slug: str,
        contact_email: str,
        contact_full_name: str,
        return_base_url: str,
        idempotency_key: str,
    ) -> dict:
        body = {
            "external_org_id": external_org_id,
            "org_name": org_name,
            "billing_email": billing_email,
            "plan_slug": plan_slug,
            "contact_email": contact_email,
            "contact_full_name": contact_full_name,
            "return_base_url": return_base_url,
        }
        return self._request(
            "POST",
            "/studio-checkout-session",
            body=body,
            idempotency_key=idempotency_key,
        )

    def cancel_studio_checkout_session(
        self,
        *,
        external_org_id: str,
        stripe_session_id: str | None,
        idempotency_key: str,
    ) -> dict:
        # 404 means Intelligence has no matching open attempt (already
        # expired by Stripe webhook, never persisted on their side, etc).
        # Treat as a successful no-op so Studio can still cancel its local
        # mirror — a stale Studio row must never block the discard UX.
        try:
            return self._request(
                "POST",
                "/studio-checkout-session/cancel",
                body={
                    "external_org_id": external_org_id,
                    "stripe_session_id": stripe_session_id,
                },
                idempotency_key=idempotency_key,
            )
        except NotFound:
            return {}

    def activate_preflight(
        self,
        *,
        session_id: str,
        expected_external_org_id: str,
        plan_slug: str,
        billing_email: str = "",
        org_name: str = "",
        contact_email: str = "",
        contact_full_name: str = "",
        recover: bool = False,
        idempotency_key: str,
    ) -> dict:
        body = {
            "session_id": session_id,
            "expected_external_org_id": expected_external_org_id,
            "plan_slug": plan_slug,
            "billing_email": billing_email,
            "org_name": org_name,
            "contact_email": contact_email,
            "contact_full_name": contact_full_name,
            "recover": recover,
        }
        return self._request(
            "POST",
            "/activate-preflight",
            body=body,
            idempotency_key=idempotency_key,
        )

    def activate_commit(
        self,
        *,
        validation_token: str,
        contact_email: str = "",
        contact_full_name: str = "",
        billing_email: str = "",
        org_name: str = "",
        idempotency_key: str,
    ) -> dict:
        body = {
            "validation_token": validation_token,
            "contact_email": contact_email,
            "contact_full_name": contact_full_name,
            "billing_email": billing_email,
            "org_name": org_name,
        }
        return self._request(
            "POST",
            "/activate-commit",
            body=body,
            idempotency_key=idempotency_key,
        )

    # ---- Account state + key rotation -----------------------------------

    def get_account(self, user_id: int | str) -> dict:
        return self._request("GET", f"/accounts/{user_id}")

    def rotate_key(self, *, user_id: int | str, external_org_id: str, idempotency_key: str) -> dict:
        return self._request(
            "POST",
            f"/accounts/{user_id}/rotate-key",
            body={"external_org_id": external_org_id},
            idempotency_key=idempotency_key,
        )

    def deactivate_keys(self, *, user_id: int | str, external_org_id: str, idempotency_key: str) -> dict:
        return self._request(
            "DELETE",
            f"/accounts/{user_id}/api-keys",
            body={"external_org_id": external_org_id},
            idempotency_key=idempotency_key,
        )

    # ---- Billing / portal -----------------------------------------------

    def portal_session(self, *, external_org_id: str) -> dict:
        return self._request(
            "POST",
            "/portal-session",
            body={"external_org_id": external_org_id},
        )

    def update_billing_contact(self, *, external_org_id: str, billing_email: str, org_name: str) -> dict:
        return self._request(
            "POST",
            "/update-billing-contact",
            body={
                "external_org_id": external_org_id,
                "billing_email": billing_email,
                "org_name": org_name,
            },
        )

    def healthz(self) -> dict:
        return self._request("GET", "/healthz")

    # ---- Internals -------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        query: dict | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        url = f"{self.base_url}{path}"
        # Serialize body deterministically, the server hashes the exact
        # bytes it received, so our hash must match. ``json.dumps`` with
        # the default options is deterministic enough since Python 3.7
        # preserves dict insertion order, but sort_keys gives us extra
        # safety against unhashed dict ordering.
        body_bytes = b""
        if body is not None:
            body_bytes = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

        # Path-with-query for the canonical signing string. The server
        # signs over ``request.path`` (Django), which is the FULL URL
        # path including the ``/internal/v1`` prefix carried in
        # ``base_url``. We must sign over the same string, using just
        # ``path`` (the relative endpoint like ``/healthz``) produces a
        # signature that always fails as ``bad_signature``.
        #
        # Use urlencode to build the query string so the canonical
        # matches what httpx puts on the wire: any value containing
        # reserved characters (``&``, ``=``, ``?``, space, ``%``)
        # would otherwise be percent-encoded by httpx but NOT in our
        # canonical, producing bad_signature. Today's call sites
        # only pass UUIDs/ints so this is forward-defense, but it
        # also closes a class of bug where a future caller could
        # smuggle attacker-controlled bytes past the HMAC integrity
        # check by exploiting the encoding discrepancy.
        from urllib.parse import urlencode, urlsplit

        full_path = urlsplit(f"{self.base_url}{path}").path
        if query:
            qs = urlencode(query, doseq=True)
            path_with_query = f"{full_path}?{qs}"
        else:
            path_with_query = full_path
            qs = ""

        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(16)
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        canonical = "\n".join(
            [
                method.upper(),
                path_with_query,
                timestamp,
                body_hash,
                self.deployment_id,
                nonce,
            ]
        ).encode("utf-8")
        signature = hmac.new(
            self.secret.encode("utf-8"),
            canonical,
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "X-Studio-Auth": signature,
            "X-Studio-Timestamp": timestamp,
            "X-Studio-Deployment-Id": self.deployment_id,
            "X-Studio-Nonce": nonce,
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        # Build the URL with query as ``httpx`` would; we already encoded
        # the same ``path_with_query`` into the signature.
        full_url = url if not qs else f"{url}?{qs}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(method, full_url, content=body_bytes, headers=headers)
        except httpx.TimeoutException as exc:
            raise ServiceUnavailable("timeout", status_code=None) from exc
        except httpx.TransportError as exc:
            raise ServiceUnavailable(f"transport: {exc}", status_code=None) from exc

        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: httpx.Response) -> dict:
        if 200 <= resp.status_code < 300:
            if not resp.content:
                return {}
            try:
                return resp.json()
            except json.JSONDecodeError:
                return {"raw": resp.text}

        # Best-effort JSON body for the error.
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {"raw": resp.text}
        code = (body or {}).get("code", "")
        # Intelligence's /internal/v1/ endpoints normally respond with
        # ``{"code": "..."}`` on errors, but DRF's AuthenticationFailed
        # is rendered through the global ``api_exception_handler`` as
        # ``{"error": {"status": 401, "detail": "<code_string>"}}``.
        # Fall back to that detail string so 401s like
        # ``deployment_not_authorized`` and ``unknown_deployment`` are
        # classified correctly (DeploymentNotAuthorized) rather than
        # collapsed into the generic InvalidApiKey path below.
        if not code:
            err = (body or {}).get("error") or {}
            if isinstance(err, dict):
                code = err.get("detail") or ""
        msg = (body or {}).get("message") or code or resp.text or "error"

        if resp.status_code == 401:
            if code in {"unknown_deployment", "deployment_not_authorized", "deployment_not_registered"}:
                raise DeploymentNotAuthorized(msg, status_code=401, code=code, body=body)
            raise InvalidApiKey(msg, status_code=401, code=code, body=body)
        if resp.status_code == 402:
            # Intelligence reuses HTTP 402 for two distinct cases:
            #   * the user has run out of credits (InsufficientCredits)
            #   * an activation Phase-1 check failed because the Stripe
            #     session isn't actually paid (``not_paid``).
            # The latter is a business-logic rejection that the activate
            # view renders cleanly; misclassifying it as
            # InsufficientCredits drops it into the worker-fallback path
            # and surfaces as a 500. Disambiguate via the response code.
            if code in _ACTIVATION_REJECTED_CODES:
                raise ActivationRejected(msg, status_code=402, code=code, body=body)
            raise InsufficientCredits(msg, status_code=402, code=code, body=body)
        if resp.status_code == 403:
            if code == "deployment_not_authorized":
                raise DeploymentNotAuthorized(msg, status_code=403, code=code, body=body)
            raise BadRequest(msg, status_code=403, code=code, body=body)
        if resp.status_code == 404:
            raise NotFound(msg, status_code=404, code=code, body=body)
        if resp.status_code == 409:
            retry_after = None
            ra = resp.headers.get("Retry-After")
            if ra is not None:
                with contextlib.suppress(ValueError):
                    retry_after = int(ra)
            raise Conflict(msg, status_code=409, code=code, body=body, retry_after=retry_after)
        if resp.status_code == 410:
            raise ActivationRejected(msg, status_code=410, code=code, body=body)
        if resp.status_code == 429:
            retry_after = None
            ra = resp.headers.get("Retry-After")
            if ra is not None:
                with contextlib.suppress(ValueError):
                    retry_after = int(ra)
            raise RateLimited(msg, status_code=429, code=code, body=body, retry_after=retry_after)
        if 400 <= resp.status_code < 500:
            if code in _ACTIVATION_REJECTED_CODES:
                raise ActivationRejected(msg, status_code=resp.status_code, code=code, body=body)
            raise BadRequest(msg, status_code=resp.status_code, code=code, body=body)
        if resp.status_code >= 500:
            raise ServiceUnavailable(msg, status_code=resp.status_code, code=code, body=body)

        raise IntelligenceClientError(msg, status_code=resp.status_code, code=code, body=body)


# ---------------------------------------------------------------------------
# IntelligenceAPIClient, per-org bearer key against /v1/
# ---------------------------------------------------------------------------


class IntelligenceAPIClient:
    """Calls Intelligence's public /v1/ tool endpoints using a per-org
    ``bb_`` bearer key (decrypted from ``IntelligenceSubscription``)."""

    def __init__(self, api_key: str, *, base_url: str | None = None, timeout: float = 30.0):
        if not api_key:
            raise ValueError("api_key required")
        self.api_key = api_key
        self.base_url = (base_url or settings.INTELLIGENCE_PUBLIC_URL).rstrip("/")
        self.timeout = timeout

    # ---- Account state --------------------------------------------------

    def me(self) -> dict:
        return self._request("GET", "/me/")

    def usage(self) -> dict:
        return self._request("GET", "/usage/")

    # ---- Tools ----------------------------------------------------------

    def score_packaging(
        self,
        *,
        title: str | None = None,
        thumbnail_url: str | None = None,
        thumbnail_base64: str | None = None,
        channel_url: str | None = None,
    ) -> dict:
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if thumbnail_url is not None:
            body["thumbnail_url"] = thumbnail_url
        if thumbnail_base64 is not None:
            body["thumbnail_base64"] = thumbnail_base64
        if channel_url is not None:
            body["channel_url"] = channel_url
        return self._request("POST", "/score/packaging", body=body)

    def score_video_hook(self, *, youtube_url: str) -> dict:
        return self._request(
            "POST",
            "/score/video-hook",
            body={"youtube_url": youtube_url},
        )

    def research_content_gaps(
        self, *, niche: str, gap_type: list[str] | None = None, limit: int = 20, min_score: int = 0
    ) -> dict:
        params = {"niche": niche, "limit": limit, "min_score": min_score}
        if gap_type:
            params["gap_type"] = ",".join(gap_type)
        return self._request("GET", "/research/content-gaps", query=params)

    def list_niches(self) -> dict:
        return self._request("GET", "/research/niches")

    def benchmark_channel(self, *, url: str) -> dict:
        return self._request("POST", "/benchmark/channel", body={"url": url})

    def benchmark_video(self, *, url: str) -> dict:
        return self._request("POST", "/benchmark/video", body={"url": url})

    # ---- Internals ------------------------------------------------------

    def _request(self, method: str, path: str, *, body: dict | None = None, query: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if body is not None:
                    resp = client.request(method, url, json=body, headers=headers, params=query)
                else:
                    resp = client.request(method, url, headers=headers, params=query)
        except httpx.TimeoutException as exc:
            raise ServiceUnavailable("timeout", status_code=None) from exc
        except httpx.TransportError as exc:
            raise ServiceUnavailable(f"transport: {exc}", status_code=None) from exc

        return InternalClient._handle_response(resp)
