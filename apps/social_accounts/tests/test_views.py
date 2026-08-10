"""Tests for social_accounts views."""

from unittest.mock import MagicMock, patch

import pytest
from django.core import signing
from django.test import override_settings
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

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={
            "facebook": {"app_id": "FB_ID", "app_secret": "FB_SECRET"},
            "threads": {"app_id": "", "app_secret": ""},
        }
    )
    def test_threads_not_offered_on_meta_credentials_alone(self, authenticated_client, workspace):
        """Threads authorizes against its own App ID, never the Facebook one.

        With only Meta credentials set, offering a Connect button would dead-end
        at Meta's error 4476002, so the platform must read as unconfigured.
        """
        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})

        # The grid renders Threads as "Not Configured" while Facebook stays live.
        grid = authenticated_client.get(url)
        assert "threads" not in grid.context["configured_platforms"]
        assert "facebook" in grid.context["configured_platforms"]

        response = authenticated_client.post(url, {"platform": "threads"})
        assert response.status_code == 302
        assert response.url == url  # bounced back to the grid, not off to Meta

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={"threads": {"app_id": "TH_ID", "app_secret": "TH_SECRET"}})
    def test_threads_connect_uses_threads_app_id(self, authenticated_client, workspace):
        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})
        response = authenticated_client.post(url, {"platform": "threads"})
        assert response.status_code == 302
        assert response.url.startswith("https://www.threads.com/oauth/authorize?")
        assert "client_id=TH_ID" in response.url

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={"threads": {"app_id": "TH_ID", "app_secret": ""}})
    def test_half_configured_platform_is_not_offered(self, authenticated_client, workspace):
        """An app id without its secret must not render a Connect button.

        The credential resolver requires both keys, so offering the button would
        walk the user through the platform's consent screen only to fail at token
        exchange with a generic "Failed to connect account".
        """
        url = reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})

        grid = authenticated_client.get(url)
        assert "threads" not in grid.context["configured_platforms"]

        response = authenticated_client.post(url, {"platform": "threads"})
        assert response.status_code == 302
        assert response.url == url

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

    def test_threads_callback_persists_a_refresh_credential(self, authenticated_client, workspace, user):
        """A Threads connect must leave the account refreshable.

        Threads returns no separate refresh token, so the provider hands back the
        long-lived access token as one. Runs the real provider with only the HTTP
        layer stubbed: if any link in that chain drops it, the account stores an
        empty oauth_refresh_token, every refresh gate skips it, and the 60-day
        token lapses silently — the original bug.
        """
        from providers.threads import ThreadsProvider

        nonce = "nonce-threads"
        state = _sign_state(workspace.id, "threads", user.id, nonce)
        session = authenticated_client.session
        session[OAUTH_SESSION_KEY] = {"nonce": nonce}
        session.save()

        responses = {
            "oauth/access_token": {"access_token": "short-lived", "user_id": "th-1"},
            "/access_token": {"access_token": "long-lived", "expires_in": 5184000},
            "/me": {"id": "th-1", "username": "tester", "name": "Tester"},
        }

        def _stub(method, url, **kwargs):
            for fragment, body in responses.items():
                if url.endswith(fragment):
                    return MagicMock(json=MagicMock(return_value=body))
            raise AssertionError(f"unexpected Threads request: {url}")

        url = reverse("social_accounts:oauth_callback", kwargs={"platform": "threads"})
        with (
            patch.object(ThreadsProvider, "_request", side_effect=_stub),
            patch(
                "apps.social_accounts.views._get_provider_for_platform",
                return_value=ThreadsProvider({"app_id": "i", "app_secret": "s"}),
            ),
        ):
            response = authenticated_client.get(url, {"code": "abc123", "state": state})

        assert response.status_code == 302
        account = SocialAccount.objects.get(workspace=workspace, platform="threads", account_platform_id="th-1")
        assert account.oauth_access_token == "long-lived"
        assert account.oauth_refresh_token == "long-lived"
        assert account.token_expires_at is not None

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


class _StubWebhookProvider:
    """A provider that really implements the webhook methods, like the Meta ones do.

    Not a MagicMock: ``_supports_webhooks`` compares the attribute on the
    provider *class* against the base class's, and ``type(MagicMock())`` has no
    such attribute — auto-speccing only reaches instances.
    """

    def __init__(self, *, error=None):
        self._error = error

    def subscribe_webhooks(self, access_token, account_id):
        if self._error:
            raise self._error
        return True


@pytest.mark.django_db
class TestRetryWebhooksView:
    """Re-running a failed subscription must not require a whole OAuth round trip.

    The warning this button lives in used to say "Reconnect the account to fix
    it" on a card whose Reconnect button only renders for a *broken* connection
    — so a healthy account with a failed subscription asked for an action the
    UI did not offer.
    """

    def _account(self, workspace, **kwargs):
        return SocialAccount.objects.create(
            workspace=workspace,
            platform="facebook",
            account_platform_id="page-1",
            account_name="Test Page",
            oauth_access_token="token123",
            webhooks_active=False,
            webhook_error="stale failure",
            **kwargs,
        )

    def _url(self, workspace, account):
        return reverse(
            "social_accounts:retry_webhooks",
            kwargs={"workspace_id": workspace.id, "account_id": account.id},
        )

    def test_a_successful_retry_clears_the_warning(self, authenticated_client, workspace):
        account = self._account(workspace)

        with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=_StubWebhookProvider()):
            response = authenticated_client.post(self._url(workspace, account))

        assert response.status_code == 302
        account.refresh_from_db()
        assert account.webhooks_active is True
        assert account.webhook_error == ""

    def test_htmx_gets_the_re_rendered_card(self, authenticated_client, workspace):
        """The button swaps its own card, so the warning has to disappear with it."""
        account = self._account(workspace)

        with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=_StubWebhookProvider()):
            response = authenticated_client.post(self._url(workspace, account), HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        body = response.content.decode()
        assert f'id="account-{account.id}"' in body
        assert "Real-time comments are off" not in body

    def test_a_still_failing_retry_re_renders_the_warning(self, authenticated_client, workspace):
        account = self._account(workspace)
        provider = _StubWebhookProvider(error=RuntimeError("still no"))

        with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
            response = authenticated_client.post(self._url(workspace, account), HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Real-time comments are off" in body
        # Still retryable, so the card keeps offering the retry rather than
        # sending the user to OAuth for a transient failure.
        assert "Try again" in body

    def test_an_auth_failure_offers_reconnect_instead_of_another_retry(self, authenticated_client, workspace):
        """A grant that cannot satisfy the call must not hand back a retry button."""
        from providers.exceptions import APIError

        account = self._account(workspace)
        provider = _StubWebhookProvider(error=APIError("nope", status_code=403))

        with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
            response = authenticated_client.post(self._url(workspace, account), HTTP_HX_REQUEST="true")

        body = response.content.decode()
        assert "Reconnect" in body
        assert "Try again" not in body

    def test_a_disconnected_account_is_not_dialled_out_for(self, authenticated_client, workspace):
        """The token is known bad; the call would spend a round trip to be refused."""
        account = self._account(workspace, connection_status=SocialAccount.ConnectionStatus.ERROR)

        with patch("apps.social_accounts.webhooks._get_provider_for_platform") as build:
            response = authenticated_client.post(self._url(workspace, account))

        assert response.status_code == 302
        build.assert_not_called()

    def test_an_unhealthy_account_is_never_offered_the_retry_button(self, authenticated_client, workspace):
        """Otherwise the card shows a button the endpoint provably refuses.

        A retryable webhook failure followed by a failed health check leaves
        webhooks_active=False on an ERROR connection — a state where "Try again"
        can only ever be a no-op. The card has to offer the reconnect instead.
        """
        self._account(workspace, connection_status=SocialAccount.ConnectionStatus.ERROR)

        response = authenticated_client.get(reverse("social_accounts:list", kwargs={"workspace_id": workspace.id}))

        body = response.content.decode()
        assert "Real-time comments are off" not in body
        assert "Try again" not in body
        assert "Reconnect" in body

    def test_the_stale_card_is_answered_with_the_reconnect_state(self, authenticated_client, workspace):
        """A card rendered while healthy can still POST after the account breaks.

        Returning the unchanged card would make the press look broken; the swap
        has to come back showing what actually helps.
        """
        account = self._account(workspace, connection_status=SocialAccount.ConnectionStatus.ERROR)

        response = authenticated_client.post(self._url(workspace, account), HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Try again" not in body
        assert "Reconnect" in body

    def test_a_token_expiring_account_may_still_retry(self, authenticated_client, workspace):
        """The token has not expired yet, so the subscription can genuinely succeed."""
        account = self._account(workspace, connection_status=SocialAccount.ConnectionStatus.TOKEN_EXPIRING)

        with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=_StubWebhookProvider()):
            authenticated_client.post(self._url(workspace, account))

        account.refresh_from_db()
        assert account.webhooks_active is True

    def test_a_press_refunds_the_automatic_retry_budget(self, authenticated_client, workspace):
        """An explicit press is a fresh mandate, even on a capped-out account."""
        from apps.social_accounts.webhooks import MAX_AUTOMATIC_RETRIES

        account = self._account(workspace, webhook_retry_count=MAX_AUTOMATIC_RETRIES)

        with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=_StubWebhookProvider()):
            authenticated_client.post(self._url(workspace, account))

        account.refresh_from_db()
        assert account.webhooks_active is True
        assert account.webhook_retry_count == 0

    def test_requires_post(self, authenticated_client, workspace):
        account = self._account(workspace)
        assert authenticated_client.get(self._url(workspace, account)).status_code == 405

    def test_requires_authentication(self, client, workspace):
        account = self._account(workspace)
        response = client.post(self._url(workspace, account))
        assert response.status_code == 302
        assert "/accounts/" in response.url

    def test_requires_the_manage_social_accounts_permission(self, client, user, organization, workspace):
        """The endpoint mutates state and calls out to the platform — a viewer must not."""
        from apps.members.models import OrgMembership, WorkspaceMembership

        OrgMembership.objects.create(user=user, organization=organization, org_role="member")
        WorkspaceMembership.objects.create(user=user, workspace=workspace, workspace_role="viewer")
        client.force_login(user)
        account = self._account(workspace)

        with patch("apps.social_accounts.webhooks._get_provider_for_platform") as build:
            response = client.post(self._url(workspace, account))

        assert response.status_code == 403
        build.assert_not_called()

    def test_another_workspaces_account_is_not_reachable(self, authenticated_client, workspace, organization):
        from apps.workspaces.models import Workspace

        other = Workspace.objects.create(name="Other WS", organization=organization)
        account = self._account(other)
        url = reverse(
            "social_accounts:retry_webhooks",
            kwargs={"workspace_id": workspace.id, "account_id": account.id},
        )
        assert authenticated_client.post(url).status_code == 404


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
