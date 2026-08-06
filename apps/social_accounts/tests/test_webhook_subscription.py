"""Connecting an account subscribes its webhooks; disconnecting removes them.

Without the subscribe call, comments and mentions never reach the inbox at all
— there is no polling fallback for them.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.social_accounts.models import SocialAccount
from apps.social_accounts.views import (
    _create_or_update_account,
    _subscribe_account_webhooks,
    _supports_webhooks,
    _unsubscribe_account_webhooks,
    _webhook_target,
)


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Webhook WS", organization=organization)


class _WebhookProvider:
    """A provider that implements the webhook methods, like the Meta ones do."""

    def __init__(self, *, subscribe=True, unsubscribe=True, error=None):
        self._subscribe = subscribe
        self._unsubscribe = unsubscribe
        self._error = error
        self.subscribe_calls = []
        self.unsubscribe_calls = []

    def subscribe_webhooks(self, access_token, account_id):
        self.subscribe_calls.append((access_token, account_id))
        if self._error:
            raise self._error
        return self._subscribe

    def unsubscribe_webhooks(self, access_token, account_id):
        self.unsubscribe_calls.append((access_token, account_id))
        if self._error:
            raise self._error
        return self._unsubscribe


def _profile(platform_id="page-1", name="Test Page"):
    return SimpleNamespace(
        platform_id=platform_id,
        name=name,
        handle="testpage",
        avatar_url="",
        follower_count=10,
    )


def _account(workspace, **kwargs):
    defaults = {
        "workspace": workspace,
        "platform": "facebook",
        "account_platform_id": "page-1",
        "account_name": "Page",
        "oauth_access_token": "page-token",
    }
    return SocialAccount.objects.create(**{**defaults, **kwargs})


# --------------------------------------------------------------- enqueueing


def test_connecting_an_account_enqueues_the_subscription(workspace):
    """The subscribe call is a network round trip, so it must not block OAuth."""
    with patch("apps.social_accounts.views._subscribe_account_webhooks_task") as task:
        account = _create_or_update_account(
            workspace_id=workspace.id,
            platform="facebook",
            profile=_profile(),
            access_token="page-token",
        )

    task.assert_called_once_with(str(account.id))


def test_instagram_remembers_the_linked_page_as_its_webhook_target(workspace):
    """IG-via-Facebook receives events on the Page, not the IG account."""
    with patch("apps.social_accounts.views._subscribe_account_webhooks_task"):
        account = _create_or_update_account(
            workspace_id=workspace.id,
            platform="instagram",
            profile=_profile(platform_id="ig-99", name="Test IG"),
            access_token="page-token",
            webhook_target_id="page-77",
        )

    assert account.webhook_target_id == "page-77"
    assert _webhook_target(account) == "page-77"


def test_webhook_target_defaults_to_the_account_itself(workspace):
    assert _webhook_target(_account(workspace, account_platform_id="page-5")) == "page-5"


# -------------------------------------------------------------- subscribing


def test_subscribe_uses_the_webhook_target(workspace):
    account = _account(workspace, platform="instagram", account_platform_id="ig-99", webhook_target_id="page-77")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _subscribe_account_webhooks(account) is True

    assert provider.subscribe_calls == [("page-token", "page-77")]


def test_a_failed_subscription_is_recorded_on_the_account(workspace):
    """The connection stays live, but the user must be able to see it is deaf."""
    account = _account(workspace)
    provider = _WebhookProvider(error=RuntimeError("Meta said no"))

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is False
    assert "not being delivered" in account.webhook_error
    # The connection itself is fine — publishing and analytics still work — and
    # last_error belongs to the periodic health check, which would wipe ours.
    assert account.connection_status == SocialAccount.ConnectionStatus.CONNECTED
    assert account.last_error == ""


def test_a_declined_subscription_is_also_recorded(workspace):
    account = _account(workspace)
    provider = _WebhookProvider(subscribe=False)

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is False
    assert "not being delivered" in account.webhook_error


def test_a_platform_without_webhooks_is_not_an_error(workspace):
    """Bluesky has no webhooks; that must not look like a failed subscription."""
    from providers.bluesky import BlueskyProvider

    account = _account(workspace, platform="bluesky")

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=BlueskyProvider({})):
        assert _subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is None
    assert account.webhook_error == ""


def test_supports_webhooks_distinguishes_real_implementations():
    from providers.bluesky import BlueskyProvider
    from providers.facebook import FacebookProvider

    assert _supports_webhooks(FacebookProvider({})) is True
    assert _supports_webhooks(BlueskyProvider({})) is False


# ------------------------------------------------------------ unsubscribing


def test_unsubscribe_uses_the_stored_webhook_target(workspace):
    account = _account(workspace, platform="instagram", account_platform_id="ig-99", webhook_target_id="page-77")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _unsubscribe_account_webhooks(account) is True

    assert provider.unsubscribe_calls == [("page-token", "page-77")]


def test_unsubscribe_failure_is_swallowed_so_disconnect_still_happens(workspace):
    account = _account(workspace)
    provider = _WebhookProvider(error=RuntimeError("gone"))

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _unsubscribe_account_webhooks(account) is False


# ---------------------------------------------------------------- the task


def test_the_background_task_skips_a_deleted_account(workspace, db):
    from apps.social_accounts.views import _subscribe_account_webhooks_task

    with patch("apps.social_accounts.views._subscribe_account_webhooks") as subscribe:
        _subscribe_account_webhooks_task.now("00000000-0000-0000-0000-000000000000")

    subscribe.assert_not_called()


def test_the_background_task_subscribes_an_existing_account(workspace):
    from apps.social_accounts.views import _subscribe_account_webhooks_task

    account = _account(workspace)
    provider = _WebhookProvider()

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        _subscribe_account_webhooks_task.now(str(account.id))

    assert provider.subscribe_calls == [("page-token", "page-1")]


# --------------------------------------------- the other multi-page entry point


@pytest.mark.django_db
def test_connection_link_flow_passes_the_page_as_the_webhook_target(client, workspace):
    """The client-facing connection link is a second Facebook/Instagram entry point.

    It has its own page loop, so an Instagram account connected by a client
    must record the linked Page just as select_account does.
    """
    from django.urls import reverse
    from django.utils import timezone

    from apps.onboarding.models import ConnectionLink
    from apps.onboarding.views import CONNECTION_LINK_OAUTH_SESSION_KEY, _sign_connection_link_state
    from providers.types import AccountProfile, OAuthTokens

    link = ConnectionLink.objects.create(
        workspace=workspace,
        expires_at=timezone.now() + timezone.timedelta(days=1),
    )
    nonce = "nonce-ig"
    state = _sign_connection_link_state(workspace.id, "instagram", link.token, nonce)
    session = client.session
    session[CONNECTION_LINK_OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(workspace.id),
        "platform": "instagram",
        "token": link.token,
        "code_verifier": "",
    }
    session.save()

    provider = MagicMock()
    provider.exchange_code.return_value = OAuthTokens(access_token="user-token", refresh_token="r", expires_in=3600)
    provider.get_profile.return_value = AccountProfile(platform_id="ig-99", name="IG")
    provider.get_user_pages.return_value = [
        {
            "id": "ig-99",
            "name": "Northlight IG",
            "handle": "northlight",
            "picture": "",
            "followers_count": 5,
            "page_id": "page-77",
            "access_token": "page-token",
        }
    ]

    with (
        patch("apps.onboarding.views._get_provider_for_platform", return_value=provider),
        patch("apps.social_accounts.views._subscribe_account_webhooks_task"),
    ):
        response = client.get(
            reverse("onboarding:oauth_callback", kwargs={"platform": "instagram"}),
            {"code": "auth-code", "state": state},
        )

    assert response.status_code == 302
    account = SocialAccount.objects.get(workspace=workspace, platform="instagram")
    assert account.webhook_target_id == "page-77"


# ------------------------------------------- subscriptions shared across rows


def test_a_shared_subscription_is_left_in_place(workspace, organization):
    """The subscription belongs to the Page, not to our row.

    The same Page can be connected in two workspaces; unsubscribing on one
    disconnect would silence the other's inbox too.
    """
    from apps.workspaces.models import Workspace

    other_ws = Workspace.objects.create(name="Other WS", organization=organization)
    account = _account(workspace, account_platform_id="page-shared")
    _account(other_ws, account_platform_id="page-shared")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _unsubscribe_account_webhooks(account) is False

    assert provider.unsubscribe_calls == []


def test_the_last_connection_does_unsubscribe(workspace, organization):
    from apps.workspaces.models import Workspace

    other_ws = Workspace.objects.create(name="Other WS", organization=organization)
    account = _account(workspace, account_platform_id="page-solo")
    # A different Page, and a disconnected row on the same Page, must not count.
    _account(other_ws, account_platform_id="page-elsewhere")
    _account(
        other_ws,
        account_platform_id="page-solo",
        connection_status=SocialAccount.ConnectionStatus.DISCONNECTED,
    )
    provider = _WebhookProvider()

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _unsubscribe_account_webhooks(account) is True

    assert provider.unsubscribe_calls == [("page-token", "page-solo")]


def test_a_shared_instagram_page_target_is_also_protected(workspace, organization):
    from apps.workspaces.models import Workspace

    other_ws = Workspace.objects.create(name="Other WS", organization=organization)
    account = _account(workspace, platform="instagram", account_platform_id="ig-1", webhook_target_id="page-77")
    _account(other_ws, platform="instagram", account_platform_id="ig-2", webhook_target_id="page-77")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        assert _unsubscribe_account_webhooks(account) is False

    assert provider.unsubscribe_calls == []


# ------------------------------------------------------- the backfill command


def test_the_backfill_command_subscribes_accounts_connected_before_this_existed(workspace):
    """Existing accounts never run the connect path, so they stay unsubscribed."""
    from io import StringIO

    from django.core.management import call_command

    account = _account(workspace, account_platform_id="page-legacy")
    assert account.webhooks_active is None
    provider = _WebhookProvider()

    out = StringIO()
    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        call_command("subscribe_webhooks", stdout=out)

    assert provider.subscribe_calls == [("page-token", "page-legacy")]
    account.refresh_from_db()
    assert account.webhooks_active is True


def test_the_backfill_command_skips_already_subscribed_accounts(workspace):
    from io import StringIO

    from django.core.management import call_command

    _account(workspace, account_platform_id="page-done", webhooks_active=True)
    provider = _WebhookProvider()

    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        call_command("subscribe_webhooks", stdout=StringIO())

    assert provider.subscribe_calls == []


def test_the_backfill_command_dry_run_calls_nothing(workspace):
    from io import StringIO

    from django.core.management import call_command

    _account(workspace, account_platform_id="page-dry")
    provider = _WebhookProvider()

    out = StringIO()
    with patch("apps.social_accounts.views._get_provider_for_platform", return_value=provider):
        call_command("subscribe_webhooks", "--dry-run", stdout=out)

    assert provider.subscribe_calls == []
    assert "would subscribe" in out.getvalue()
