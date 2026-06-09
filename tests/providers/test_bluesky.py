"""Tests for Bluesky provider session handling."""

import base64
import json
import time
from unittest.mock import MagicMock, patch

from providers.bluesky import BlueskyProvider, _access_jwt_expires_in


def _make_jwt(payload: dict) -> str:
    """Build a JWT-shaped string (header.payload.signature) — signature is unchecked."""

    def encode(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{encode({'alg': 'HS256'})}.{encode(payload)}.signature"


class TestAccessJwtExpiresIn:
    def test_returns_positive_for_future_exp(self):
        future = int(time.time()) + 3600
        jwt = _make_jwt({"exp": future})
        result = _access_jwt_expires_in(jwt)
        assert result is not None
        assert 3595 <= result <= 3600

    def test_returns_zero_for_past_exp(self):
        past = int(time.time()) - 300
        jwt = _make_jwt({"exp": past})
        assert _access_jwt_expires_in(jwt) == 0

    def test_returns_none_for_malformed_jwt(self):
        assert _access_jwt_expires_in("not-a-jwt") is None
        assert _access_jwt_expires_in("only.two") is None
        assert _access_jwt_expires_in("a.!!!notbase64!!!.c") is None

    def test_returns_none_when_exp_missing(self):
        jwt = _make_jwt({"sub": "did:plc:abc"})
        assert _access_jwt_expires_in(jwt) is None

    def test_returns_none_when_exp_not_numeric(self):
        jwt = _make_jwt({"exp": "tomorrow"})
        assert _access_jwt_expires_in(jwt) is None


class TestCreateSession:
    @patch.object(BlueskyProvider, "_request")
    def test_populates_expires_in_from_jwt(self, mock_request):
        future = int(time.time()) + 7200
        access_jwt = _make_jwt({"exp": future})
        mock_request.return_value = MagicMock(
            json=MagicMock(return_value={"accessJwt": access_jwt, "refreshJwt": "refresh"}),
        )

        provider = BlueskyProvider()
        tokens = provider.create_session("user.bsky.social", "app-pw")

        assert tokens.access_token == access_jwt
        assert tokens.refresh_token == "refresh"
        assert tokens.expires_in is not None
        assert 7195 <= tokens.expires_in <= 7200


class TestRefreshToken:
    @patch.object(BlueskyProvider, "_request")
    def test_populates_expires_in_from_jwt(self, mock_request):
        future = int(time.time()) + 3600
        access_jwt = _make_jwt({"exp": future})
        mock_request.return_value = MagicMock(
            json=MagicMock(return_value={"accessJwt": access_jwt, "refreshJwt": "new-refresh"}),
        )

        provider = BlueskyProvider()
        tokens = provider.refresh_token("old-refresh")

        assert tokens.access_token == access_jwt
        assert tokens.refresh_token == "new-refresh"
        assert tokens.expires_in is not None
        assert 3595 <= tokens.expires_in <= 3600
