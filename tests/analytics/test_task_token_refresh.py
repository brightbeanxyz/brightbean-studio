"""Tests for analytics sync OAuth token handling."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from apps.analytics.tasks import _call_with_analytics_token
from providers.exceptions import APIError
from providers.types import AuthType, OAuthTokens


class _ConnectionStatus:
    CONNECTED = "connected"


def test_analytics_call_refreshes_and_retries_on_invalid_credentials():
    account = SimpleNamespace(
        oauth_access_token="stale-access",
        oauth_refresh_token="refresh-token",
        token_expires_at=None,
        connection_status="connected",
        ConnectionStatus=_ConnectionStatus,
        is_token_expiring_soon=False,
        save=MagicMock(),
    )
    provider = MagicMock()
    provider.auth_type = AuthType.OAUTH2
    provider.refresh_token.return_value = OAuthTokens(
        access_token="fresh-access",
        refresh_token="new-refresh",
        expires_in=3600,
    )
    call = MagicMock(
        side_effect=[
            APIError(
                "YouTube API error 401: Invalid Credentials",
                status_code=401,
                raw_response={"error": {"message": "Invalid Credentials"}},
            ),
            "ok",
        ]
    )

    assert _call_with_analytics_token(account, provider, call) == "ok"
    provider.refresh_token.assert_called_once_with("refresh-token")
    assert account.oauth_access_token == "fresh-access"
    assert account.oauth_refresh_token == "new-refresh"
    assert account.token_expires_at is not None
    account.save.assert_called_once()
    assert call.call_args_list[0].args == ("stale-access",)
    assert call.call_args_list[1].args == ("fresh-access",)
