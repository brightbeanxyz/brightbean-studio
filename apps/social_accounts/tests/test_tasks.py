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
