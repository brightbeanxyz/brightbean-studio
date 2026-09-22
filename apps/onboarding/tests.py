"""Tests for the connection-link OAuth flow — PKCE round-trip for TikTok.

The connection-link flow is a second, public OAuth entry point (separate from
social_accounts.connect_platform). It must apply PKCE for providers that need
it (TikTok), otherwise the authorize URL lacks code_challenge and TikTok
rejects it with errCode=10007.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.onboarding.models import ConnectionLink
from apps.onboarding.views import CONNECTION_LINK_OAUTH_SESSION_KEY, _sign_connection_link_state
from providers.types import AccountProfile, OAuthTokens


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Test WS", organization=organization)


@pytest.fixture
def connection_link(db, workspace):
    return ConnectionLink.objects.create(
        workspace=workspace,
        expires_at=timezone.now() + timezone.timedelta(days=1),
    )


@pytest.mark.django_db
class TestConnectionLinkPkce:
    def test_oauth_start_generates_and_forwards_verifier(self, client, workspace, connection_link):
        from apps.credentials.models import PlatformCredential

        PlatformCredential.objects.create(
            organization=workspace.organization,
            platform="tiktok",
            credentials={"client_key": "k", "client_secret": "s"},
            is_configured=True,
        )

        mock_provider = MagicMock()
        mock_provider.uses_pkce = True
        mock_provider.get_auth_url.return_value = "https://www.tiktok.com/v2/auth/authorize/?ok=1"

        url = reverse("onboarding:connection_oauth_start", kwargs={"token": connection_link.token})
        with patch("apps.onboarding.views._get_provider_for_platform", return_value=mock_provider):
            response = client.post(url, {"platform": "tiktok"})

        assert response.status_code == 302
        verifier = client.session[CONNECTION_LINK_OAUTH_SESSION_KEY]["code_verifier"]
        assert verifier  # non-empty
        _, kwargs = mock_provider.get_auth_url.call_args
        assert kwargs["code_verifier"] == verifier

    def test_oauth_callback_replays_verifier(self, client, workspace, connection_link):
        nonce = "nonce-xyz"
        verifier = "stored-connection-verifier"
        state = _sign_connection_link_state(workspace.id, "tiktok", connection_link.token, nonce)
        session = client.session
        session[CONNECTION_LINK_OAUTH_SESSION_KEY] = {
            "nonce": nonce,
            "workspace_id": str(workspace.id),
            "platform": "tiktok",
            "token": connection_link.token,
            "code_verifier": verifier,
        }
        session.save()

        mock_provider = MagicMock()
        mock_provider.exchange_code.return_value = OAuthTokens(access_token="tok", refresh_token="r", expires_in=3600)
        mock_provider.get_profile.return_value = AccountProfile(platform_id="open-1", name="TT")

        url = reverse("onboarding:oauth_callback", kwargs={"platform": "social1"})
        with patch("apps.onboarding.views._get_provider_for_platform", return_value=mock_provider):
            response = client.get(url, {"code": "auth-code", "state": state})

        assert response.status_code == 302
        mock_provider.exchange_code.assert_called_once()
        _, kwargs = mock_provider.exchange_code.call_args
        assert kwargs["code_verifier"] == verifier


@pytest.mark.django_db
class TestConnectionLinkPageTokens:
    """A Page must be driven by its own token, and a Page we had to skip must
    not leave the client on a success page for an account never connected."""

    def _callback(self, client, workspace, connection_link, pages):
        nonce = "nonce-pages"
        state = _sign_connection_link_state(workspace.id, "facebook", connection_link.token, nonce)
        session = client.session
        session[CONNECTION_LINK_OAUTH_SESSION_KEY] = {
            "nonce": nonce,
            "workspace_id": str(workspace.id),
            "platform": "facebook",
            "token": connection_link.token,
        }
        session.save()

        provider = MagicMock()
        provider.exchange_code.return_value = OAuthTokens(access_token="USER-TOKEN", refresh_token="", expires_in=None)
        provider.get_profile.return_value = AccountProfile(platform_id="me-1", name="Owner")
        provider.get_user_pages.return_value = pages

        url = reverse("onboarding:oauth_callback", kwargs={"platform": "facebook"})
        with (
            patch("apps.onboarding.views._get_provider_for_platform", return_value=provider),
            patch("apps.social_accounts.views.subscribe_account_webhooks_task"),
        ):
            response = client.get(url, {"code": "auth-code", "state": state})
        return response

    def test_a_page_is_connected_with_its_own_token(self, client, workspace, connection_link):
        from apps.social_accounts.models import SocialAccount

        response = self._callback(
            client,
            workspace,
            connection_link,
            [{"id": "page-1", "name": "Page One", "access_token": "PAGE-TOKEN"}],
        )

        assert response.status_code == 302
        account = SocialAccount.objects.get(account_platform_id="page-1")
        assert account.oauth_access_token == "PAGE-TOKEN"
        assert "connection_link_error" not in client.session

    def test_a_page_without_its_own_token_is_reported_not_silently_dropped(self, client, workspace, connection_link):
        from apps.social_accounts.models import SocialAccount

        response = self._callback(
            client,
            workspace,
            connection_link,
            [
                {"id": "page-1", "name": "Page One", "access_token": "PAGE-TOKEN"},
                {"id": "page-2", "name": "Page Two"},
            ],
        )

        assert response.status_code == 302
        assert SocialAccount.objects.filter(account_platform_id="page-1").exists()
        # Never connected with the user token as a stand-in.
        assert not SocialAccount.objects.filter(account_platform_id="page-2").exists()
        error = client.session["connection_link_error"]
        assert "Page Two" in error
        assert "Page One" not in error
