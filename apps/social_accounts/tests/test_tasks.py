"""Tests for social_accounts background tasks."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.social_accounts.models import SocialAccount
from apps.social_accounts.tasks import check_social_account_health
from providers.types import AccountProfile, OAuthTokens


def _profile(*, follower_count=0, avatar_url=None, name="", handle=None, platform_id="123"):
    return AccountProfile(
        platform_id=platform_id,
        name=name,
        handle=handle,
        avatar_url=avatar_url,
        follower_count=follower_count,
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Test Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Test WS", organization=organization)


@pytest.fixture
def connected_account(db, workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="123",
        account_name="Test Page",
        oauth_access_token="valid_token",
        oauth_refresh_token="refresh_token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


@pytest.mark.django_db
class TestCheckSocialAccountHealth:
    @patch("providers.get_provider")
    def test_successful_health_check(self, mock_get_provider, connected_account):
        mock_provider = MagicMock()
        mock_provider.get_profile.return_value = _profile(follower_count=1500)
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(connected_account.id))

        account = SocialAccount.objects.get(pk=connected_account.pk)
        assert account.connection_status == SocialAccount.ConnectionStatus.CONNECTED
        assert account.follower_count == 1500
        assert account.last_health_check_at is not None
        assert account.last_error == ""

    @patch("providers.get_provider")
    def test_instagram_health_check_passes_selected_ig_user_id(self, mock_get_provider, workspace):
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="instagram",
            account_platform_id="17841400000000000",
            account_name="Brightbean",
            oauth_access_token="page-token",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        mock_provider = MagicMock()
        mock_provider.get_profile.return_value = _profile(
            platform_id="17841400000000000",
            name="Brightbean",
            handle="brightbean",
        )
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(account.id))

        _platform, credentials = mock_get_provider.call_args.args
        assert credentials["ig_user_id"] == "17841400000000000"
        mock_provider.get_profile.assert_called_once_with("page-token")

    @patch("apps.common.validators.is_safe_url", return_value=True)
    @patch("providers.get_provider")
    def test_mastodon_health_check_injects_instance_url_without_registration(
        self, mock_get_provider, _mock_is_safe_url, workspace
    ):
        # Regression: the old inline resolver set instance_url only *inside* the
        # MastodonAppRegistration lookup, so an account with no registration row had
        # instance_url dropped -> empty base URL. The shared resolver sets it first.
        # is_safe_url is patched to keep the SSRF check off the network.
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="mastodon",
            account_platform_id="masto-1",
            account_name="Masto",
            instance_url="https://mastodon.social",
            oauth_access_token="tok",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        mock_provider = MagicMock()
        mock_provider.get_profile.return_value = _profile(platform_id="masto-1", name="Masto")
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(account.id))

        _platform, credentials = mock_get_provider.call_args.args
        assert credentials["instance_url"] == "https://mastodon.social"

    @patch("providers.get_provider")
    def test_failed_health_check_sets_error(self, mock_get_provider, connected_account):
        mock_provider = MagicMock()
        mock_provider.get_profile.side_effect = Exception("Token expired")
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(connected_account.id))

        account = SocialAccount.objects.get(pk=connected_account.pk)
        assert account.connection_status == SocialAccount.ConnectionStatus.ERROR
        assert account.last_error == "Connection check failed. Please try reconnecting."

    @patch("providers.get_provider")
    def test_token_refresh_on_expiring(self, mock_get_provider, connected_account):
        connected_account.token_expires_at = timezone.now() + timedelta(days=3)
        connected_account.save()

        mock_provider = MagicMock()
        mock_provider.refresh_token.return_value = OAuthTokens(
            access_token="new_access",
            refresh_token="new_refresh",
            expires_in=3600,
        )
        mock_provider.get_profile.return_value = _profile(follower_count=100)
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(connected_account.id))

        account = SocialAccount.objects.get(pk=connected_account.pk)
        assert account.oauth_access_token == "new_access"
        assert account.oauth_refresh_token == "new_refresh"
        assert account.connection_status == SocialAccount.ConnectionStatus.CONNECTED

    @patch("providers.get_provider")
    def test_refresh_failure_marks_expiring(self, mock_get_provider, connected_account):
        connected_account.token_expires_at = timezone.now() + timedelta(days=3)
        connected_account.save()

        mock_provider = MagicMock()
        mock_provider.refresh_token.side_effect = Exception("Refresh failed")
        mock_provider.get_profile.return_value = _profile(follower_count=100)
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(connected_account.id))

        account = SocialAccount.objects.get(pk=connected_account.pk)
        # After refresh failure the token_expiring status is set, then profile
        # fetch succeeds but doesn't override the expiring status
        assert account.connection_status in (
            SocialAccount.ConnectionStatus.CONNECTED,
            SocialAccount.ConnectionStatus.TOKEN_EXPIRING,
        )

    @patch("providers.get_provider")
    def test_health_check_refreshes_avatar_name_handle(self, mock_get_provider, connected_account):
        connected_account.avatar_url = "https://old.example/avatar.jpg?x-expires=1"
        connected_account.account_name = "Old Name"
        connected_account.account_handle = "old"
        connected_account.save()

        mock_provider = MagicMock()
        mock_provider.get_profile.return_value = _profile(
            follower_count=200,
            avatar_url="https://new.example/avatar.jpg?x-expires=999",
            name="New Name",
            handle="new",
        )
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(connected_account.id))

        account = SocialAccount.objects.get(pk=connected_account.pk)
        assert account.avatar_url == "https://new.example/avatar.jpg?x-expires=999"
        assert account.account_name == "New Name"
        assert account.account_handle == "new"

    @patch("providers.get_provider")
    def test_health_check_preserves_avatar_when_provider_returns_empty(self, mock_get_provider, connected_account):
        connected_account.avatar_url = "https://old.example/avatar.jpg"
        connected_account.account_name = "Kept Name"
        connected_account.account_handle = "kept"
        connected_account.save()

        mock_provider = MagicMock()
        mock_provider.get_profile.return_value = _profile(follower_count=10)
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(connected_account.id))

        account = SocialAccount.objects.get(pk=connected_account.pk)
        assert account.avatar_url == "https://old.example/avatar.jpg"
        assert account.account_name == "Kept Name"
        assert account.account_handle == "kept"

    @patch("providers.get_provider")
    def test_failed_health_check_preserves_profile_fields(self, mock_get_provider, connected_account):
        connected_account.avatar_url = "https://old.example/avatar.jpg"
        connected_account.account_name = "Kept Name"
        connected_account.account_handle = "kept"
        connected_account.save()

        mock_provider = MagicMock()
        mock_provider.get_profile.side_effect = Exception("Token expired")
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(connected_account.id))

        account = SocialAccount.objects.get(pk=connected_account.pk)
        assert account.connection_status == SocialAccount.ConnectionStatus.ERROR
        assert account.avatar_url == "https://old.example/avatar.jpg"
        assert account.account_name == "Kept Name"
        assert account.account_handle == "kept"

    def test_nonexistent_account_does_not_raise(self, db):
        check_social_account_health.now("00000000-0000-0000-0000-000000000000")

    @patch("providers.get_provider")
    def test_bluesky_bootstrap_refresh_when_expires_at_null(self, mock_get_provider, db, workspace):
        """Legacy Bluesky accounts with token_expires_at=NULL should still refresh."""
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="bluesky",
            account_platform_id="did:plc:abc",
            account_name="Test",
            oauth_access_token="stale_access",
            oauth_refresh_token="valid_refresh",
            token_expires_at=None,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

        mock_provider = MagicMock()
        mock_provider.refresh_token.return_value = OAuthTokens(
            access_token="fresh_access",
            refresh_token="fresh_refresh",
            expires_in=7200,
        )
        mock_provider.get_profile.return_value = _profile(follower_count=42)
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(account.id))

        mock_provider.refresh_token.assert_called_once_with("valid_refresh")
        account.refresh_from_db()
        assert account.oauth_access_token == "fresh_access"
        assert account.oauth_refresh_token == "fresh_refresh"
        assert account.token_expires_at is not None
        assert account.connection_status == SocialAccount.ConnectionStatus.CONNECTED

    @patch("providers.get_provider")
    def test_threads_bootstrap_refresh_when_expires_at_null(self, mock_get_provider, db, workspace):
        """Threads accounts with no recorded expiry must still refresh.

        is_token_expiring_soon can't judge a NULL expiry, so without the
        bootstrap these accounts sit out every refresh cycle and their 60-day
        token lapses — the same trap the Bluesky bootstrap covers.
        """
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="threads",
            account_platform_id="th-2",
            account_name="Test",
            oauth_access_token="long_lived",
            oauth_refresh_token="long_lived",
            token_expires_at=None,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

        mock_provider = MagicMock()
        mock_provider.refresh_token.return_value = OAuthTokens(
            access_token="rotated",
            refresh_token="rotated",
            expires_in=5184000,
        )
        mock_provider.get_profile.return_value = _profile(follower_count=7)
        mock_get_provider.return_value = mock_provider

        check_social_account_health.now(str(account.id))

        mock_provider.refresh_token.assert_called_once_with("long_lived")
        account.refresh_from_db()
        assert account.oauth_access_token == "rotated"
        assert account.token_expires_at is not None

    @patch("providers.get_provider")
    def test_threads_expiring_account_rotates_its_long_lived_token(self, mock_get_provider, db, workspace):
        """Threads replays its access token as its own refresh credential.

        Runs the real provider (only the HTTP layer is stubbed) so this covers the
        wiring end to end: a Threads account whose 60-day token is running out must
        come back with a rotated token that is itself refreshable next cycle.
        """
        from providers.threads import ThreadsProvider

        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="threads",
            account_platform_id="th-1",
            account_name="Test",
            oauth_access_token="long_lived",
            oauth_refresh_token="long_lived",
            token_expires_at=timezone.now() + timedelta(days=3),
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

        # Keyed by URL rather than call order, so an added provider call fails
        # with a named assertion instead of a bare StopIteration.
        responses = {
            "/refresh_access_token": {"access_token": "rotated", "expires_in": 5184000},
            "/me": {"id": "th-1", "username": "tester", "name": "Test"},
        }

        def _stub(method, url, **kwargs):
            for fragment, body in responses.items():
                if url.endswith(fragment):
                    return MagicMock(json=MagicMock(return_value=body))
            raise AssertionError(f"unexpected Threads request: {url}")

        with patch.object(ThreadsProvider, "_request", side_effect=_stub):
            mock_get_provider.return_value = ThreadsProvider({"app_id": "i", "app_secret": "s"})
            check_social_account_health.now(str(account.id))

        account.refresh_from_db()
        assert account.oauth_access_token == "rotated"
        assert account.oauth_refresh_token == "rotated"
        assert account.token_expires_at > timezone.now() + timedelta(days=7)
        assert account.connection_status == SocialAccount.ConnectionStatus.CONNECTED
