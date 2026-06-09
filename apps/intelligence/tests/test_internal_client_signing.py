"""HMAC signing tests for InternalClient.

The wire-level format must match Intelligence's verifier exactly. These
tests build the canonical signing string locally and assert the client
produces a matching signature for the same input.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

import httpx
import pytest
from django.test import SimpleTestCase, override_settings

from apps.intelligence.services.client import InternalClient
from apps.intelligence.services.exceptions import (
    ActivationRejected,
    Conflict,
    DeploymentNotAuthorized,
    InsufficientCredits,
    NotFound,
    RateLimited,
    ServiceUnavailable,
)

_BASE_URL = "https://intel.example.com/internal/v1"


@override_settings(
    INTELLIGENCE_INTERNAL_URL=_BASE_URL,
    STUDIO_DEPLOYMENT_ID="prod",
    STUDIO_SHARED_SECRET="test-secret",
)
class TestSigningCanonical(SimpleTestCase):
    def _canonical(self, method, path_with_query, timestamp, body_bytes, nonce, secret="test-secret"):
        body_hash = hashlib.sha256(body_bytes or b"").hexdigest()
        canonical = "\n".join(
            [
                method.upper(),
                path_with_query,
                timestamp,
                body_hash,
                "prod",
                nonce,
            ]
        ).encode("utf-8")
        return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()

    def test_get_request_signature(self):
        with patch("apps.intelligence.services.client.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_resp = httpx.Response(200, json={"plans": []})
            mock_client.request.return_value = mock_resp

            InternalClient().list_plans()

            call = mock_client.request.call_args
            method = call.args[0]
            url = call.args[1]
            headers = call.kwargs["headers"]

            assert method == "GET"
            assert url == f"{_BASE_URL}/plans"
            # Server-derived deployment id matches header value.
            assert headers["X-Studio-Deployment-Id"] == "prod"
            # Recompute expected signature for the actual headers used.
            # The client signs over the FULL URL path including the
            # ``/internal/v1`` prefix from base_url (matches what
            # Django's ``request.path`` produces server-side); using
            # just ``/plans`` here would produce a non-matching hash.
            expected = self._canonical(
                "GET",
                "/internal/v1/plans",
                headers["X-Studio-Timestamp"],
                b"",
                headers["X-Studio-Nonce"],
            )
            assert headers["X-Studio-Auth"] == expected

    def test_post_request_signature_includes_body_hash(self):
        with patch("apps.intelligence.services.client.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_resp = httpx.Response(200, json={"checkout_url": "https://stripe.example/x"})
            mock_client.request.return_value = mock_resp

            InternalClient().studio_checkout_session(
                external_org_id="org_uuid",
                org_name="Acme",
                billing_email="finance@acme.com",
                plan_slug="hobby",
                contact_email="alice@acme.com",
                contact_full_name="Alice",
                return_base_url="https://studio.example.com",
                idempotency_key="checkout-prod-org_uuid",
            )

            call = mock_client.request.call_args
            headers = call.kwargs["headers"]
            body_bytes = call.kwargs["content"]

            # Idempotency key is forwarded.
            assert headers["X-Idempotency-Key"] == "checkout-prod-org_uuid"
            # Body is canonical JSON (sorted keys, no whitespace).
            decoded = json.loads(body_bytes)
            assert decoded["external_org_id"] == "org_uuid"
            assert decoded["plan_slug"] == "hobby"
            # Recompute expected signature.
            expected = self._canonical(
                "POST",
                "/internal/v1/studio-checkout-session",
                headers["X-Studio-Timestamp"],
                body_bytes,
                headers["X-Studio-Nonce"],
            )
            assert headers["X-Studio-Auth"] == expected

    def test_nonces_differ_across_requests(self):
        with patch("apps.intelligence.services.client.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.request.return_value = httpx.Response(200, json={})

            client = InternalClient()
            client.list_plans()
            client.list_plans()

            calls = mock_client.request.call_args_list
            nonce_a = calls[0].kwargs["headers"]["X-Studio-Nonce"]
            nonce_b = calls[1].kwargs["headers"]["X-Studio-Nonce"]
            assert nonce_a != nonce_b

    def test_query_string_in_signed_path(self):
        with patch("apps.intelligence.services.client.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.request.return_value = httpx.Response(200, json={})

            InternalClient().check_eligibility(external_org_id="abc-uuid")
            call = mock_client.request.call_args
            headers = call.kwargs["headers"]
            expected = self._canonical(
                "GET",
                "/internal/v1/check-eligibility?external_org_id=abc-uuid",
                headers["X-Studio-Timestamp"],
                b"",
                headers["X-Studio-Nonce"],
            )
            assert headers["X-Studio-Auth"] == expected


@override_settings(
    INTELLIGENCE_INTERNAL_URL=_BASE_URL,
    STUDIO_DEPLOYMENT_ID="prod",
    STUDIO_SHARED_SECRET="test-secret",
)
class TestErrorMapping(SimpleTestCase):
    def _client_returning(self, status, body=None, *, headers=None):
        ctx = patch("apps.intelligence.services.client.httpx.Client")
        mock_client_cls = ctx.start()
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.request.return_value = httpx.Response(
            status,
            json=body or {},
            headers=headers or {},
        )
        return InternalClient(), ctx

    def test_402_raises_insufficient_credits(self):
        client, ctx = self._client_returning(402, {"code": "no_credits"})
        try:
            with pytest.raises(InsufficientCredits):
                client.list_plans()
        finally:
            ctx.stop()

    def test_404_raises_not_found(self):
        """``get_account`` does not swallow 404 (unlike pending_activation)."""
        client, ctx = self._client_returning(404, {"code": "not_found"})
        try:
            with pytest.raises(NotFound):
                client.get_account(user_id=123)
        finally:
            ctx.stop()

    def test_pending_activation_404_returns_none(self):
        """Special-case: pending_activation swallows NotFound and returns None
        so the caller can branch on 'is there pending state' cleanly."""
        client, ctx = self._client_returning(404, {"code": "not_found"})
        try:
            assert client.pending_activation(external_org_id="x") is None
        finally:
            ctx.stop()

    def test_409_raises_conflict_with_retry_after(self):
        client, ctx = self._client_returning(
            409,
            {"code": "in_progress"},
            headers={"Retry-After": "5"},
        )
        try:
            with pytest.raises(Conflict) as exc_info:
                client.list_plans()
            assert exc_info.value.retry_after == 5
        finally:
            ctx.stop()

    def test_410_raises_activation_rejected(self):
        client, ctx = self._client_returning(410, {"code": "token_expired"})
        try:
            with pytest.raises(ActivationRejected) as exc_info:
                client.activate_commit(
                    validation_token="x",
                    idempotency_key="commit-x",
                )
            assert exc_info.value.code == "token_expired"
            # User-message mapping.
            assert "expired" in exc_info.value.user_message.lower()
        finally:
            ctx.stop()

    def test_429_carries_retry_after(self):
        client, ctx = self._client_returning(
            429,
            {"code": "rate_limited"},
            headers={"Retry-After": "30"},
        )
        try:
            with pytest.raises(RateLimited) as exc_info:
                client.list_plans()
            assert exc_info.value.retry_after == 30
        finally:
            ctx.stop()

    def test_403_deployment_not_authorized(self):
        client, ctx = self._client_returning(
            403,
            {"code": "deployment_not_authorized"},
        )
        try:
            with pytest.raises(DeploymentNotAuthorized):
                client.list_plans()
        finally:
            ctx.stop()

    def test_500_raises_service_unavailable(self):
        client, ctx = self._client_returning(500, {"code": "oops"})
        try:
            with pytest.raises(ServiceUnavailable):
                client.list_plans()
        finally:
            ctx.stop()

    def test_400_with_unknown_code_is_bad_request(self):
        client, ctx = self._client_returning(400, {"code": "invalid_request"})
        try:
            from apps.intelligence.services.exceptions import BadRequest

            with pytest.raises(BadRequest):
                client.list_plans()
        finally:
            ctx.stop()

    def test_400_with_activation_code_is_activation_rejected(self):
        client, ctx = self._client_returning(
            400,
            {"code": "unknown_checkout_attempt"},
        )
        try:
            with pytest.raises(ActivationRejected):
                client.activate_preflight(
                    session_id="cs_x",
                    expected_external_org_id="x",
                    plan_slug="hobby",
                    idempotency_key="preflight-x",
                )
        finally:
            ctx.stop()
