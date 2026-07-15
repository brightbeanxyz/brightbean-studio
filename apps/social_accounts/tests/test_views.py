"""Tests for social_accounts views."""

from unittest.mock import MagicMock, patch

import pytest
from django.core import signing
from django.urls import reverse

from apps.social_accounts.models import SocialAccount
from apps.social_accounts.views import OAUTH_SESSION_KEY, _sign_state, _unsign_state
from providers.types import AccountProfile, OAuthTokens


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Test WS", organization=organization)


@pytest.fixture
def manager_setup(db, user, organization, workspace):
    """Set up user as org owner + workspace manager."""
    from apps.members.models import OrgMembership, WorkspaceMembership

    OrgMembership.objects.create(user=user, organization=organization, org_role="owner")
    WorkspaceMembership.objects.create(user=user, workspace=workspace, workspace_role="manager")
    return user


@pytest.fixture
def authenticated_client(client, user, manager_setup):
    client.force_login(user)
    return client


class TestOAuthState:
    """Test OAuth state parameter signing and validation."""

    def test_sign_and_unsign_state(self):
        state = _sign_state("ws-123", "facebook", "user-456", "nonce-789")
        data = _unsign_state(state)
        assert data["workspace_id"] == "ws-123"
        assert data["platform"] == "facebook"
        assert data["user_id"] == "user-456"
        assert data["nonce"] == "nonce-789"

    def test_expired_state_raises(self):
        state = _sign_state("ws-123", "facebook", "user-456", "nonce")
        with pytest.raises(signing.BadSignature):
            signing.loads(state, salt="social-oauth-state", max_age=0)

    def test_tampered_state_raises(self):
        state = _sign_state("ws-123", "facebook", "user-456", "nonce")
        with pytest.raises(signing.BadSignature):
            _unsign_state(state + "tampered")


@pytest.mark.django_db
class TestAccountListView:
    def test_requires_authentication(self, client, workspace):
        url = reverse("social_accounts:list", kwargs={"workspace_id": workspace.id})
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/" in response.url

    def test_returns_200_for_authenticated_user(self, authenticated_client, workspace):
        url = reverse("social_accounts:list", kwargs={"workspace_id": workspace.id})
        response = authenticated_client.get(url)
        assert response.status_code == 200

    def test_shows_connected_accounts(self, authenticated_client, workspace):
        SocialAccount.objects.create(
            workspace=workspace,
            platform="facebook",
            account_platform_id="123",
            account_name="My Facebook Page",
        )
        url = reverse("social_accounts:list", kwargs={"workspace_id": workspace.id})
        response = authenticated_client.get(url)
        assert b"My Facebook Page" in response.content

    def test_shows_empty_state(self, authenticated_client, workspace):
        url = reverse("social_accounts:list", kwargs={"workspace_id": workspace.id})
        response = authenticated_client.get(url)
        assert b"No accounts connected yet" in response.content


@pytest.mark.django_db
class TestConnectPlatformView:
    def test_get_shows_platform_grid(self, authenticated_client, workspace):
        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert b"Connect a Platform" in response.content

    def test_post_invalid_platform(self, authenticated_client, workspace):
        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})
        response = authenticated_client.post(url, {"platform": "twitter"})
        assert response.status_code == 302

    def test_post_bluesky_redirects_to_form(self, authenticated_client, workspace):
        from apps.credentials.models import PlatformCredential

        PlatformCredential.objects.create(
            organization=workspace.organization,
            platform="bluesky",
            credentials={"handle": "test"},
            is_configured=True,
        )
        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})
        response = authenticated_client.post(url, {"platform": "bluesky"})
        assert response.status_code == 302
        assert "bluesky" in response.url

    def test_pkce_connect_generates_and_forwards_verifier(self, authenticated_client, workspace):
        """A PKCE provider (TikTok) gets a code_verifier stashed in the session
        and forwarded to get_auth_url so it can derive the code_challenge."""
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

        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})
        with patch("apps.social_accounts.views._get_provider_for_platform", return_value=mock_provider):
            response = authenticated_client.post(url, {"platform": "tiktok"})

        assert response.status_code == 302
        assert response.url == "https://www.tiktok.com/v2/auth/authorize/?ok=1"

        verifier = authenticated_client.session[OAUTH_SESSION_KEY]["code_verifier"]
        assert verifier  # non-empty
        _, kwargs = mock_provider.get_auth_url.call_args
        assert kwargs["code_verifier"] == verifier

    def test_non_pkce_connect_omits_verifier(self, authenticated_client, workspace):
        """A non-PKCE provider stores code_verifier=None and is called without it."""
        from apps.credentials.models import PlatformCredential

        PlatformCredential.objects.create(
            organization=workspace.organization,
            platform="facebook",
            credentials={"client_id": "i", "client_secret": "s"},
            is_configured=True,
        )

        mock_provider = MagicMock()
        mock_provider.uses_pkce = False
        mock_provider.get_auth_url.return_value = "https://facebook.example/auth"

        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})
        with patch("apps.social_accounts.views._get_provider_for_platform", return_value=mock_provider):
            response = authenticated_client.post(url, {"platform": "facebook"})

        assert response.status_code == 302
        assert authenticated_client.session[OAUTH_SESSION_KEY]["code_verifier"] is None
        _, kwargs = mock_provider.get_auth_url.call_args
        assert "code_verifier" not in kwargs


@pytest.mark.django_db
class TestReconnectView:
    def test_pkce_reconnect_generates_and_forwards_verifier(self, authenticated_client, workspace):
        """Reconnecting a TikTok account must regenerate + forward a PKCE verifier;
        reconnect previously sent no code_challenge -> TikTok errCode 10007."""
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="tiktok",
            account_platform_id="open-1",
            account_name="My TikTok",
        )

        mock_provider = MagicMock()
        mock_provider.uses_pkce = True
        mock_provider.get_auth_url.return_value = "https://www.tiktok.com/v2/auth/authorize/?ok=1"

        url = reverse(
            "social_accounts:reconnect",
            kwargs={"workspace_id": workspace.id, "account_id": account.id},
        )
        with patch("apps.social_accounts.views._get_provider_for_platform", return_value=mock_provider):
            response = authenticated_client.post(url)

        assert response.status_code == 302
        verifier = authenticated_client.session[OAUTH_SESSION_KEY]["code_verifier"]
        assert verifier  # non-empty
        _, kwargs = mock_provider.get_auth_url.call_args
        assert kwargs["code_verifier"] == verifier


@pytest.mark.django_db
class TestOAuthCallbackView:
    def test_error_parameter_shows_message(self, authenticated_client):
        url = reverse("social_accounts:oauth_callback", kwargs={"platform": "facebook"})
        response = authenticated_client.get(url, {"error": "access_denied", "error_description": "User denied"})
        assert response.status_code == 302

    def test_missing_code_shows_error(self, authenticated_client):
        url = reverse("social_accounts:oauth_callback", kwargs={"platform": "facebook"})
        response = authenticated_client.get(url, {"state": "somestate"})
        assert response.status_code == 302

    def test_invalid_state_shows_error(self, authenticated_client):
        url = reverse("social_accounts:oauth_callback", kwargs={"platform": "facebook"})
        response = authenticated_client.get(url, {"code": "abc123", "state": "invalid_state"})
        assert response.status_code == 302

    def test_instagram_redirects_to_account_selection(self, authenticated_client, workspace, user):
        nonce = "nonce-123"
        state = _sign_state(workspace.id, "instagram", user.id, nonce)
        session = authenticated_client.session
        session[OAUTH_SESSION_KEY] = {"nonce": nonce}
        session.save()

        mock_provider = MagicMock()
        mock_provider.exchange_code.return_value = OAuthTokens(access_token="user-token", refresh_token="refresh")
        mock_provider.get_user_pages.return_value = [
            {
                "id": "17841400000000000",
                "name": "Brightbean",
                "handle": "brightbean",
                "access_token": "page-token",
            }
        ]
        url = reverse("social_accounts:oauth_callback", kwargs={"platform": "instagram"})

        with patch("apps.social_accounts.views._get_provider_for_platform", return_value=mock_provider):
            response = authenticated_client.get(url, {"code": "abc123", "state": state})

        assert response.status_code == 302
        assert response.url == reverse("social_accounts:select_account")
        mock_provider.get_profile.assert_not_called()
        page_data = authenticated_client.session["oauth_page_select"]
        assert page_data["platform"] == "instagram"
        assert page_data["pages"][0]["id"] == "17841400000000000"

    def test_tiktok_callback_replays_pkce_verifier(self, authenticated_client, workspace, user):
        """The verifier stashed at connect is read from the session and replayed
        on the TikTok token exchange (callback arrives at the ``social1`` slug)."""
        nonce = "nonce-tiktok"
        verifier = "stored-code-verifier"
        state = _sign_state(workspace.id, "tiktok", user.id, nonce)
        session = authenticated_client.session
        session[OAUTH_SESSION_KEY] = {"nonce": nonce, "code_verifier": verifier}
        session.save()

        mock_provider = MagicMock()
        mock_provider.exchange_code.return_value = OAuthTokens(access_token="tok", refresh_token="r", expires_in=3600)
        mock_provider.get_profile.return_value = AccountProfile(platform_id="open-id-1", name="Test TikTok")

        url = reverse("social_accounts:oauth_callback", kwargs={"platform": "social1"})
        with patch("apps.social_accounts.views._get_provider_for_platform", return_value=mock_provider):
            response = authenticated_client.get(url, {"code": "auth-code", "state": state})

        assert response.status_code == 302
        mock_provider.exchange_code.assert_called_once()
        _, kwargs = mock_provider.exchange_code.call_args
        assert kwargs["code_verifier"] == verifier


@pytest.mark.django_db
class TestSelectAccountView:
    def test_blank_page_access_token_falls_back_to_user_token(self, authenticated_client, workspace):
        session = authenticated_client.session
        session["oauth_page_select"] = {
            "workspace_id": str(workspace.id),
            "platform": "instagram",
            "user_tokens": {
                "access_token": "user-token",
                "refresh_token": "refresh-token",
            },
            "pages": [
                {
                    "id": "17841400000000000",
                    "name": "Brightbean",
                    "handle": "brightbean",
                    "access_token": "",
                }
            ],
        }
        session.save()

        url = reverse("social_accounts:select_account")
        response = authenticated_client.post(url, {"selected_pages": ["17841400000000000"]})

        assert response.status_code == 302
        account = SocialAccount.objects.get(
            workspace=workspace,
            platform="instagram",
            account_platform_id="17841400000000000",
        )
        assert account.oauth_access_token == "user-token"
        assert account.oauth_refresh_token == "refresh-token"

    def test_facebook_page_without_access_token_is_not_connected(self, authenticated_client, workspace):
        session = authenticated_client.session
        session["oauth_page_select"] = {
            "workspace_id": str(workspace.id),
            "platform": "facebook",
            "user_tokens": {
                "access_token": "user-token",
                "refresh_token": "refresh-token",
            },
            "pages": [
                {
                    "id": "page-1",
                    "name": "Brightbean Page",
                    "access_token": "",
                }
            ],
        }
        session.save()

        url = reverse("social_accounts:select_account")
        response = authenticated_client.post(url, {"selected_pages": ["page-1"]})

        assert response.status_code == 302
        assert not SocialAccount.objects.filter(
            workspace=workspace,
            platform="facebook",
            account_platform_id="page-1",
        ).exists()


@pytest.mark.django_db
class TestDisconnectView:
    def test_disconnect_removes_account(self, authenticated_client, workspace):
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="facebook",
            account_platform_id="123",
            account_name="Test Page",
            oauth_access_token="token123",
        )
        url = reverse(
            "social_accounts:disconnect",
            kwargs={"workspace_id": workspace.id, "account_id": account.id},
        )
        with patch("apps.social_accounts.views._get_provider_for_platform") as mock:
            mock_provider = MagicMock()
            mock_provider.revoke_token.return_value = True
            mock.return_value = mock_provider
            response = authenticated_client.post(url)

        assert response.status_code == 302
        assert SocialAccount.objects.filter(pk=account.pk).count() == 0

    def test_disconnect_requires_post(self, authenticated_client, workspace):
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="facebook",
            account_platform_id="123",
            account_name="Test Page",
        )
        url = reverse(
            "social_accounts:disconnect",
            kwargs={"workspace_id": workspace.id, "account_id": account.id},
        )
        response = authenticated_client.get(url)
        assert response.status_code == 405


@pytest.mark.django_db
class TestBlueskyConnectView:
    def test_get_shows_form(self, authenticated_client, workspace):
        url = reverse(
            "social_accounts:connect_bluesky",
            kwargs={"workspace_id": workspace.id},
        )
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert b"Connect Bluesky" in response.content

    def test_post_requires_handle_and_password(self, authenticated_client, workspace):
        url = reverse(
            "social_accounts:connect_bluesky",
            kwargs={"workspace_id": workspace.id},
        )
        response = authenticated_client.post(url, {"handle": "", "app_password": ""})
        assert response.status_code == 200


@pytest.mark.django_db
class TestMastodonConnectView:
    def test_get_shows_form(self, authenticated_client, workspace):
        url = reverse(
            "social_accounts:connect_mastodon",
            kwargs={"workspace_id": workspace.id},
        )
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert b"Connect Mastodon" in response.content
