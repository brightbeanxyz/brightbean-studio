"""Connecting an account subscribes its webhooks; disconnecting removes them.

Without the subscribe call, comments reach the inbox only on the five-minute
polling cycle instead of instantly — degraded, not broken, which is what the
warning and its retry button have to convey.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.social_accounts.error_messages import (
    WEBHOOK_GENERIC_MESSAGE,
    WEBHOOK_RECONNECT_MESSAGE,
    WEBHOOK_REJECTED_MESSAGE,
    WEBHOOK_UNAVAILABLE_MESSAGE,
)
from apps.social_accounts.models import SocialAccount
from apps.social_accounts.views import _create_or_update_account
from apps.social_accounts.webhooks import (
    MAX_AUTOMATIC_RETRIES,
    retry_failed_subscription,
    subscribe_account_webhooks,
    supports_webhooks,
    unsubscribe_account_webhooks,
    webhook_target,
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
    with patch("apps.social_accounts.views.subscribe_account_webhooks_task") as task:
        account = _create_or_update_account(
            workspace_id=workspace.id,
            platform="facebook",
            profile=_profile(),
            access_token="page-token",
        )

    task.assert_called_once_with(str(account.id))


def test_reconnecting_clears_a_previous_webhook_failure(workspace):
    """The warning must not outlive the reconnect it asked for.

    A stale False would otherwise survive a perfectly good new grant — leaving
    the card telling the user to do the thing they just did.
    """
    _account(
        workspace,
        account_platform_id="page-1",
        webhooks_active=False,
        webhook_error="an old failure",
        webhook_needs_reconnect=True,
    )

    with patch("apps.social_accounts.views.subscribe_account_webhooks_task"):
        account = _create_or_update_account(
            workspace_id=workspace.id,
            platform="facebook",
            profile=_profile(),
            access_token="fresh-token",
        )

    assert account.webhooks_active is None
    assert account.webhook_error == ""
    assert account.webhook_needs_reconnect is False


def test_instagram_remembers_the_linked_page_as_its_webhook_target(workspace):
    """IG-via-Facebook receives events on the Page, not the IG account."""
    with patch("apps.social_accounts.views.subscribe_account_webhooks_task"):
        account = _create_or_update_account(
            workspace_id=workspace.id,
            platform="instagram",
            profile=_profile(platform_id="ig-99", name="Test IG"),
            access_token="page-token",
            webhook_target_id="page-77",
        )

    assert account.webhook_target_id == "page-77"
    # Stored for _is_own_activity, but NOT what we subscribe: comments/mentions
    # are Instagram-object fields and a Page rejects them outright.
    assert webhook_target(account) == "ig-99"


def test_webhook_target_is_always_the_account_itself(workspace):
    assert webhook_target(_account(workspace, account_platform_id="page-5")) == "page-5"


# -------------------------------------------------------------- subscribing


def test_subscribe_targets_the_instagram_user_not_its_linked_page(workspace):
    """Meta answers comments/mentions on a Page with "(#100) Param
    subscribed_fields[0] must be one of {feed, mention, ...}", so every account
    subscribed against the Page was left with a permanently deaf inbox."""
    account = _account(workspace, platform="instagram", account_platform_id="ig-99", webhook_target_id="page-77")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert subscribe_account_webhooks(account) is True

    assert provider.subscribe_calls == [("page-token", "ig-99")]


def test_a_failed_subscription_is_recorded_on_the_account(workspace):
    """The connection stays live, but the user must be able to see it is degraded."""
    account = _account(workspace)
    provider = _WebhookProvider(error=RuntimeError("Meta said no"))

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is False
    assert account.webhook_error == WEBHOOK_GENERIC_MESSAGE
    # Retryable in place: nothing here says the grant is the problem.
    assert account.webhook_needs_reconnect is False
    # The connection itself is fine — publishing and analytics still work — and
    # last_error belongs to the periodic health check, which would wipe ours.
    assert account.connection_status == SocialAccount.ConnectionStatus.CONNECTED
    assert account.last_error == ""


def test_a_declined_subscription_is_also_recorded(workspace):
    account = _account(workspace)
    provider = _WebhookProvider(subscribe=False)

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is False
    assert account.webhook_error == WEBHOOK_REJECTED_MESSAGE


def test_the_stored_message_never_carries_the_platforms_payload(workspace):
    """The card renders webhook_error verbatim.

    The bug this guards: Meta's rejection arrived as
    ``APIError('Instagram API error 400: {"error":{"message":"(#100) Param
    subscribed_fields[0] must be one of {feed, mention, ...')`` — built from
    ``response.text[:500]`` — and was shown to the user, truncated mid-token.
    """
    from providers.exceptions import APIError

    account = _account(workspace)
    payload = '{"error":{"message":"(#100) Param subscribed_fields[0] must be one of {feed, mention, name"}}'
    provider = _WebhookProvider(error=APIError(f"Instagram API error 400: {payload}", status_code=400))

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        subscribe_account_webhooks(account)

    account.refresh_from_db()
    assert account.webhook_error == WEBHOOK_REJECTED_MESSAGE
    assert "subscribed_fields" not in account.webhook_error
    assert '{"' not in account.webhook_error


def test_an_auth_failure_asks_for_a_reconnect_instead_of_a_retry(workspace):
    """A 403 means the grant can't satisfy the call; retrying it forever won't help."""
    from providers.exceptions import APIError

    account = _account(workspace)
    provider = _WebhookProvider(error=APIError("nope", status_code=403))

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        subscribe_account_webhooks(account)

    account.refresh_from_db()
    assert account.webhook_needs_reconnect is True
    assert account.webhook_error == WEBHOOK_RECONNECT_MESSAGE


def test_a_later_success_clears_the_reconnect_prompt(workspace):
    account = _account(workspace, webhooks_active=False, webhook_needs_reconnect=True, webhook_error="stale")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert subscribe_account_webhooks(account) is True

    account.refresh_from_db()
    assert account.webhooks_active is True
    assert account.webhook_error == ""
    assert account.webhook_needs_reconnect is False


def test_a_platform_without_webhooks_is_not_an_error(workspace):
    """Bluesky has no webhooks; that must not look like a failed subscription."""
    from providers.bluesky import BlueskyProvider

    account = _account(workspace, platform="bluesky")

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=BlueskyProvider({})):
        assert subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is None
    assert account.webhook_error == ""


def test_supports_webhooks_distinguishes_real_implementations():
    from providers.bluesky import BlueskyProvider
    from providers.facebook import FacebookProvider

    assert supports_webhooks(FacebookProvider({})) is True
    assert supports_webhooks(BlueskyProvider({})) is False


# ------------------------------------------------------------ unsubscribing


def test_unsubscribe_targets_the_same_object_subscribe_did(workspace):
    account = _account(workspace, platform="instagram", account_platform_id="ig-99", webhook_target_id="page-77")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert unsubscribe_account_webhooks(account) is True

    assert provider.unsubscribe_calls == [("page-token", "ig-99")]


def test_unsubscribe_failure_is_swallowed_so_disconnect_still_happens(workspace):
    account = _account(workspace)
    provider = _WebhookProvider(error=RuntimeError("gone"))

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert unsubscribe_account_webhooks(account) is False


# ---------------------------------------------------------------- the task


def test_the_background_task_skips_a_deleted_account(workspace, db):
    from apps.social_accounts.webhooks import subscribe_account_webhooks_task

    with patch("apps.social_accounts.webhooks.subscribe_account_webhooks") as subscribe:
        subscribe_account_webhooks_task.now("00000000-0000-0000-0000-000000000000")

    subscribe.assert_not_called()


def test_the_background_task_subscribes_an_existing_account(workspace):
    from apps.social_accounts.webhooks import subscribe_account_webhooks_task

    account = _account(workspace)
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        subscribe_account_webhooks_task.now(str(account.id))

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
        patch("apps.social_accounts.views.subscribe_account_webhooks_task"),
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

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert unsubscribe_account_webhooks(account) is False

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

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert unsubscribe_account_webhooks(account) is True

    assert provider.unsubscribe_calls == [("page-token", "page-solo")]


def test_the_same_instagram_account_in_two_workspaces_is_protected(workspace, organization):
    """The subscription belongs to the IG user, so a second workspace holding
    the same account still depends on it."""
    from apps.workspaces.models import Workspace

    other_ws = Workspace.objects.create(name="Other WS", organization=organization)
    account = _account(workspace, platform="instagram", account_platform_id="ig-1", webhook_target_id="page-77")
    _account(other_ws, platform="instagram", account_platform_id="ig-1", webhook_target_id="page-77")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert unsubscribe_account_webhooks(account) is False

    assert provider.unsubscribe_calls == []


def test_two_instagram_accounts_sharing_a_page_do_not_share_a_subscription(workspace, organization):
    """Each IG user carries its own subscription now, so disconnecting one must
    not leave the other's dangling."""
    from apps.workspaces.models import Workspace

    other_ws = Workspace.objects.create(name="Other WS", organization=organization)
    account = _account(workspace, platform="instagram", account_platform_id="ig-1", webhook_target_id="page-77")
    _account(other_ws, platform="instagram", account_platform_id="ig-2", webhook_target_id="page-77")
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert unsubscribe_account_webhooks(account) is True

    assert provider.unsubscribe_calls == [("page-token", "ig-1")]


# ------------------------------------------------------- the backfill command


def test_the_backfill_command_subscribes_accounts_connected_before_this_existed(workspace):
    """Existing accounts never run the connect path, so they stay unsubscribed."""
    from io import StringIO

    from django.core.management import call_command

    account = _account(workspace, account_platform_id="page-legacy")
    assert account.webhooks_active is None
    provider = _WebhookProvider()

    out = StringIO()
    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        call_command("subscribe_webhooks", stdout=out)

    assert provider.subscribe_calls == [("page-token", "page-legacy")]
    account.refresh_from_db()
    assert account.webhooks_active is True


def test_the_backfill_command_skips_already_subscribed_accounts(workspace):
    from io import StringIO

    from django.core.management import call_command

    _account(workspace, account_platform_id="page-done", webhooks_active=True)
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        call_command("subscribe_webhooks", stdout=StringIO())

    assert provider.subscribe_calls == []


def test_the_backfill_command_dry_run_calls_nothing(workspace):
    from io import StringIO

    from django.core.management import call_command

    _account(workspace, account_platform_id="page-dry")
    provider = _WebhookProvider()

    out = StringIO()
    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        call_command("subscribe_webhooks", "--dry-run", stdout=out)

    assert provider.subscribe_calls == []
    assert "would subscribe" in out.getvalue()


# ------------------------------------- outcomes recorded even when not attempted


def test_a_provider_that_cannot_be_built_is_recorded(workspace):
    """Otherwise "Try again" re-renders an identical card and looks broken.

    Returning False without touching the row left the user pressing a button
    that produced no visible change and no error, forever.
    """
    account = _account(workspace)

    with patch(
        "apps.social_accounts.webhooks._get_provider_for_platform",
        side_effect=RuntimeError("no credentials"),
    ):
        assert subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is False
    assert account.webhook_error == WEBHOOK_UNAVAILABLE_MESSAGE
    assert account.webhook_needs_reconnect is False


def test_a_platform_that_lost_webhook_support_clears_its_stale_warning(workspace):
    """A False recorded when the provider *did* subscribe must not outlive it.

    Nobody can act on a warning about a platform that no longer has webhooks at
    all, so the honest state is "not applicable".
    """
    from providers.bluesky import BlueskyProvider

    account = _account(
        workspace,
        platform="bluesky",
        webhooks_active=False,
        webhook_error="left over from when this platform had webhooks",
        webhook_needs_reconnect=True,
        webhook_retry_count=3,
    )

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=BlueskyProvider({})):
        assert subscribe_account_webhooks(account) is False

    account.refresh_from_db()
    assert account.webhooks_active is None
    assert account.webhook_error == ""
    assert account.webhook_needs_reconnect is False
    assert account.webhook_retry_count == 0


def test_the_raw_provider_text_is_kept_for_operators(workspace):
    """diagnose_facebook needs the error code the user-facing copy throws away."""
    from providers.exceptions import APIError

    account = _account(workspace)
    raw = 'Instagram API error 400: {"error":{"message":"(#100) Param subscribed_fields[0]","fbtrace_id":"Au5i"}}'
    provider = _WebhookProvider(error=APIError(raw, status_code=400))

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        subscribe_account_webhooks(account)

    account.refresh_from_db()
    assert "fbtrace_id" in account.webhook_error_detail
    # ...and still never in the field the card renders.
    assert "fbtrace_id" not in account.webhook_error


# --------------------------------------------------- the automatic retry budget


def test_each_failure_spends_one_retry(workspace):
    account = _account(workspace)
    provider = _WebhookProvider(subscribe=False)

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        subscribe_account_webhooks(account)
        account.refresh_from_db()
        assert account.webhook_retry_count == 1
        subscribe_account_webhooks(account)

    account.refresh_from_db()
    assert account.webhook_retry_count == 2


def test_a_success_refunds_the_budget(workspace):
    account = _account(workspace, webhooks_active=False, webhook_retry_count=4)
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert subscribe_account_webhooks(account) is True

    account.refresh_from_db()
    assert account.webhook_retry_count == 0


def test_the_automatic_retry_stops_once_the_budget_is_spent(workspace):
    """A permanent rejection must not be re-sent to the platform every cycle."""
    account = _account(workspace, webhooks_active=False, webhook_retry_count=MAX_AUTOMATIC_RETRIES)
    provider = _WebhookProvider(subscribe=False)

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert retry_failed_subscription(account) is False

    assert provider.subscribe_calls == []


def test_the_automatic_retry_runs_while_budget_remains(workspace):
    account = _account(workspace, webhooks_active=False, webhook_retry_count=MAX_AUTOMATIC_RETRIES - 1)
    provider = _WebhookProvider()

    with patch("apps.social_accounts.webhooks._get_provider_for_platform", return_value=provider):
        assert retry_failed_subscription(account) is True

    assert provider.subscribe_calls == [("page-token", "page-1")]


def test_reconnecting_refunds_the_automatic_retry_budget(workspace):
    _account(workspace, account_platform_id="page-1", webhooks_active=False, webhook_retry_count=MAX_AUTOMATIC_RETRIES)

    with patch("apps.social_accounts.views.subscribe_account_webhooks_task"):
        account = _create_or_update_account(
            workspace_id=workspace.id,
            platform="facebook",
            profile=_profile(),
            access_token="fresh-token",
        )

    assert account.webhook_retry_count == 0
