"""The inbox sync engine suppresses first-sync history but never the first real message."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.inbox.models import InboxMessage
from apps.inbox.tasks import InboxSyncEngine
from apps.social_accounts.models import SocialAccount
from providers.exceptions import APIError, QuotaExceededError, TokenExpiredError
from providers.instagram import InstagramProvider
from providers.types import OAuthTokens
from providers.youtube import YouTubeMessageBatch


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Sync WS", organization=organization)


@pytest.fixture
def connected_account(db, workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-sync-1",
        account_name="Sync Test",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


def _msg(message_id, *, minutes_ago=0, text="hello"):
    """A minimal stand-in for the message objects providers return."""
    return SimpleNamespace(
        platform_message_id=message_id,
        sender_name="Sender",
        sender_id="sender-1",
        text=text,
        message_type=InboxMessage.MessageType.DM,
        timestamp=timezone.now() - timedelta(minutes=minutes_ago),
        extra={},
    )


@pytest.mark.django_db
def test_first_sync_suppresses_old_backlog_then_notifies_new(connected_account):
    with patch("apps.inbox.tasks.get_provider") as get_provider:
        provider = get_provider.return_value

        # First-ever sync pulls an OLD historical backlog -> seed it silently.
        provider.get_messages.return_value = [_msg("h1", minutes_ago=1440), _msg("h2", minutes_ago=2880)]
        with patch.object(InboxSyncEngine, "_notify_new_message") as notify_new:
            InboxSyncEngine().sync_all()
        assert InboxMessage.objects.filter(social_account=connected_account).count() == 2
        notify_new.assert_not_called()

        # Once the account has history, a genuinely new message notifies.
        provider.get_messages.return_value = [_msg("n1", minutes_ago=0)]
        with patch.object(InboxSyncEngine, "_notify_new_message") as notify_new:
            InboxSyncEngine().sync_all()
        notify_new.assert_called_once()


@pytest.mark.django_db
def test_first_message_on_quiet_account_still_notifies(connected_account):
    # Regression: a long-quiet account has no prior messages, so last_msg is None
    # and it's still the "first sync" — but its first genuinely-recent message must
    # alert, not be silently swallowed as if it were backlog.
    with patch("apps.inbox.tasks.get_provider") as get_provider:
        get_provider.return_value.get_messages.return_value = [_msg("first", minutes_ago=0)]
        with patch.object(InboxSyncEngine, "_notify_new_message") as notify_new:
            InboxSyncEngine().sync_all()
        notify_new.assert_called_once()


@pytest.mark.parametrize("comments_fail", [False, True])
def test_instagram_poll_continuation_survives_a_fresh_worker(connected_account, comments_fail):
    connected_account.webhook_target_id = "page-1"
    connected_account.oauth_access_token = "page-token"
    connected_account.save()
    calls = []

    def request(method, url, **kwargs):
        after = kwargs["params"].get("after")
        calls.append((url, after))
        if url.endswith("/conversations"):
            data = {"data": [{"id": "busy"}, {"id": "later"}]}
        elif url.endswith("/busy/messages"):
            page = int(after or "0")
            data = {"data": []}
            if page < 99:
                data["paging"] = {"next": "https://untrusted/token", "cursors": {"after": str(page + 1)}}
        else:
            data = {
                "data": [
                    {
                        "id": "later-dm",
                        "from": {"id": "customer"},
                        "created_time": timezone.now().isoformat(),
                        "message": "Question",
                    }
                ]
            }
        return SimpleNamespace(json=lambda: data)

    def factory(platform, credentials):
        instance = InstagramProvider(credentials)
        instance._fetch_media_comments = MagicMock(return_value=[])
        if comments_fail:
            instance._fetch_media_comments.side_effect = APIError("comment grant rejected", status_code=403)
        instance._request = MagicMock(side_effect=request)
        return instance

    with patch("apps.inbox.tasks.get_provider", side_effect=factory):
        InboxSyncEngine().sync_all()
        connected_account.refresh_from_db()
        assert connected_account.instagram_dm_poll_state["message_after"] == "99"
        assert not InboxMessage.objects.filter(social_account=connected_account).exists()
        with patch.object(InboxSyncEngine, "_notify_new_message"):
            InboxSyncEngine().sync_all()

    connected_account.refresh_from_db()
    assert connected_account.instagram_dm_poll_state == {}
    assert calls[100][0].endswith("/busy/messages")
    assert calls[100][1] == "99"
    assert InboxMessage.objects.filter(social_account=connected_account, platform_message_id="later-dm").exists()


@pytest.mark.parametrize("failure_mode", ["dm_failed", "import_failed"])
def test_instagram_failed_poll_keeps_previous_continuation(connected_account, failure_mode):
    from providers.meta_messaging import InstagramMessageBatch

    previous = {"conversations": ["retry-this-page"]}
    connected_account.instagram_dm_poll_state = previous
    connected_account.save()
    batch = InstagramMessageBatch([_msg("comment-or-dm")], poll_state=None if failure_mode == "dm_failed" else {})
    instance = MagicMock()
    instance.get_messages.return_value = batch
    engine = InboxSyncEngine()
    with patch("apps.inbox.tasks.get_provider", return_value=instance):
        if failure_mode == "import_failed":
            with (
                patch.object(engine, "_upsert_message", side_effect=RuntimeError("storage failed")),
                pytest.raises(RuntimeError, match="storage failed"),
            ):
                engine._sync_account(connected_account)
        else:
            with patch.object(engine, "_notify_new_message"):
                engine._sync_account(connected_account)
    connected_account.refresh_from_db()
    assert connected_account.instagram_dm_poll_state == previous


@pytest.mark.django_db
def test_mastodon_sync_passes_per_account_instance_url(workspace):
    # Regression: sync used to call get_provider(platform) with no credentials, so the
    # federated MastodonProvider got instance_url="" and built scheme-less URLs like
    # "/api/v1/notifications" -> httpx.UnsupportedProtocol. The account's instance_url
    # must reach the provider. is_safe_url is patched so the SSRF check stays hermetic
    # (it does a real DNS lookup otherwise).
    from apps.social_accounts.models import MastodonAppRegistration

    # Persisted so sync_all() picks it up; referenced only via the DB query.
    SocialAccount.objects.create(
        workspace=workspace,
        platform="mastodon",
        account_platform_id="masto-1",
        account_name="Masto Test",
        instance_url="https://mastodon.social",
        oauth_access_token="tok",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    MastodonAppRegistration.objects.create(
        instance_url="https://mastodon.social",
        client_id="cid",
        client_secret="csecret",
    )

    with (
        patch("apps.inbox.tasks.get_provider") as get_provider,
        patch("apps.common.validators.is_safe_url", return_value=True),
    ):
        get_provider.return_value.get_messages.return_value = []
        InboxSyncEngine().sync_all()

    get_provider.assert_called_once()
    platform, credentials = get_provider.call_args.args
    assert platform == "mastodon"
    assert credentials["instance_url"] == "https://mastodon.social"


def _comment(message_id, *, post_id="", minutes_ago=0):
    return SimpleNamespace(
        platform_message_id=message_id,
        sender_name="Commenter",
        sender_id="user-9",
        text="Nice post",
        message_type=InboxMessage.MessageType.COMMENT,
        timestamp=timezone.now() - timedelta(minutes=minutes_ago),
        extra={"stored_post_id": post_id} if post_id else {},
    )


def _youtube_account(workspace, *, expires_in=None):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="youtube",
        account_platform_id="yt-sync-1",
        account_name="YouTube Sync Test",
        oauth_access_token="old-token",
        oauth_refresh_token="refresh-token",
        token_expires_at=timezone.now() + expires_in if expires_in is not None else None,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


@pytest.mark.django_db
def test_youtube_inbox_preflight_refresh_does_not_queue_analytics_backfill(workspace):
    account = _youtube_account(workspace, expires_in=timedelta(minutes=2))
    provider = MagicMock()
    provider.refresh_token.return_value = OAuthTokens(access_token="fresh-token", expires_in=3600)
    provider.get_messages.return_value = []

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        patch("apps.analytics.tasks.backfill_account_analytics") as backfill,
    ):
        InboxSyncEngine().sync_all()

    account.refresh_from_db()
    assert account.oauth_access_token == "fresh-token"
    provider.refresh_token.assert_called_once_with("refresh-token")
    provider.get_messages.assert_called_once()
    kwargs = provider.get_messages.call_args.kwargs
    assert (kwargs["access_token"], kwargs["since"], kwargs["deep"]) == ("fresh-token", None, False)
    assert kwargs["channel_id"] == "yt-sync-1"
    backfill.assert_not_called()


@pytest.mark.django_db
def test_youtube_inbox_token_with_headroom_is_not_refreshed(workspace):
    _youtube_account(workspace, expires_in=timedelta(minutes=50))
    provider = MagicMock()
    provider.get_messages.return_value = []

    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    provider.refresh_token.assert_not_called()
    provider.get_messages.assert_called_once()
    kwargs = provider.get_messages.call_args.kwargs
    assert (kwargs["access_token"], kwargs["since"], kwargs["deep"]) == ("old-token", None, False)
    assert kwargs["channel_id"] == "yt-sync-1"


@pytest.mark.django_db
def test_youtube_inbox_unknown_expiry_refreshes_after_rejection_and_upserts_once(workspace):
    account = _youtube_account(workspace)
    provider = MagicMock()
    provider.refresh_token.return_value = OAuthTokens(access_token="fresh-token", expires_in=3600)
    provider.get_messages.side_effect = [
        TokenExpiredError("secret response", status_code=401, raw_response={"error": {"status": "UNAUTHENTICATED"}}),
        [_comment("recovered-comment")],
    ]

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        patch.object(InboxSyncEngine, "_notify_new_message"),
    ):
        InboxSyncEngine().sync_all()

    assert provider.get_messages.call_count == 2
    assert provider.get_messages.call_args.kwargs["access_token"] == "fresh-token"
    assert provider.refresh_token.call_count == 1
    assert InboxMessage.objects.filter(social_account=account, platform_message_id="recovered-comment").count() == 1


@pytest.mark.django_db
def test_youtube_inbox_uses_token_rotated_by_another_worker(workspace):
    account = _youtube_account(workspace)
    provider = MagicMock()

    def get_messages(*, access_token, since, deep=False, **_quota_kwargs):
        if access_token == "old-token":
            SocialAccount.objects.filter(pk=account.pk).update(oauth_access_token="rotated-token")
            raise TokenExpiredError("expired", status_code=401)
        return []

    provider.get_messages.side_effect = get_messages
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    assert [call.kwargs["access_token"] for call in provider.get_messages.call_args_list] == [
        "old-token",
        "rotated-token",
    ]
    provider.refresh_token.assert_not_called()


@pytest.mark.django_db
def test_youtube_inbox_permanent_refresh_refusal_requests_health_check(workspace, caplog):
    _youtube_account(workspace)
    provider = MagicMock()
    provider.get_messages.side_effect = TokenExpiredError("expired", status_code=401)
    provider.refresh_token.side_effect = APIError(
        "secret response", status_code=400, raw_response={"error": "invalid_grant"}
    )

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        patch("apps.inbox.tasks._queue_health_check") as health,
    ):
        InboxSyncEngine().sync_all()

    health.assert_called_once()
    assert provider.get_messages.call_count == 1
    assert provider.refresh_token.call_count == 1
    assert "secret response" not in caplog.text


@pytest.mark.django_db
def test_youtube_inbox_transient_refresh_failure_does_not_request_reconnect(workspace):
    _youtube_account(workspace)
    provider = MagicMock()
    provider.get_messages.side_effect = TokenExpiredError("expired", status_code=401)
    provider.refresh_token.side_effect = APIError("gateway", status_code=503)

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        patch("apps.inbox.tasks._queue_health_check") as health,
    ):
        InboxSyncEngine().sync_all()

    health.assert_not_called()
    assert provider.get_messages.call_count == 1
    assert provider.refresh_token.call_count == 1


@pytest.mark.django_db
def test_youtube_inbox_stops_after_refreshed_token_is_rejected(workspace):
    _youtube_account(workspace)
    provider = MagicMock()
    provider.get_messages.side_effect = TokenExpiredError("expired", status_code=401)
    provider.refresh_token.return_value = OAuthTokens(access_token="fresh-token", expires_in=3600)

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        patch("apps.inbox.tasks._queue_health_check") as health,
    ):
        InboxSyncEngine().sync_all()

    assert provider.get_messages.call_count == 2
    assert provider.refresh_token.call_count == 1
    health.assert_called_once()


@pytest.mark.django_db
def test_youtube_inbox_repeated_poll_upserts_without_duplicate_notification(workspace):
    account = _youtube_account(workspace)
    provider = MagicMock()
    provider.get_messages.return_value = [_comment("same-comment")]

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        patch.object(InboxSyncEngine, "_notify_new_message") as notify_new,
    ):
        InboxSyncEngine().sync_all()
        InboxSyncEngine().sync_all()

    assert InboxMessage.objects.filter(social_account=account, platform_message_id="same-comment").count() == 1
    notify_new.assert_called_once()


@pytest.mark.django_db
def test_mastodon_503_does_not_stop_other_accounts(workspace):
    SocialAccount.objects.create(
        workspace=workspace,
        platform="mastodon",
        account_platform_id="masto-sync-1",
        account_name="Mastodon Sync Test",
        oauth_access_token="mastodon-token",
    )
    instagram = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-sync-2",
        account_name="Instagram Sync Test",
        oauth_access_token="instagram-token",
    )
    mastodon_provider = MagicMock()
    mastodon_provider.get_messages.side_effect = APIError("upstream unavailable", status_code=503)
    instagram_provider = MagicMock()
    instagram_provider.get_messages.return_value = [_msg("still-polled")]

    with (
        patch("apps.publisher.engine._resolve_publish_credentials", return_value={}),
        patch(
            "apps.inbox.tasks.get_provider",
            side_effect={"mastodon": mastodon_provider, "instagram": instagram_provider}.get,
        ),
        patch.object(InboxSyncEngine, "_notify_new_message"),
    ):
        InboxSyncEngine().sync_all()

    assert InboxMessage.objects.filter(social_account=instagram, platform_message_id="still-polled").exists()


@pytest.mark.django_db
def test_a_polled_comment_links_to_the_post_it_belongs_to(connected_account):
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=connected_account.workspace, caption="hi")
    platform_post = PlatformPost.objects.create(
        post=post,
        social_account=connected_account,
        status=PlatformPost.Status.PUBLISHED,
        platform_post_id="post-1",
    )

    with patch("apps.inbox.tasks.get_provider") as get_provider:
        get_provider.return_value.get_messages.return_value = [
            _comment("c1", post_id="post-1"),
            _comment("c2", post_id="post-unknown"),
            _comment("c3"),
        ]
        InboxSyncEngine().sync_all()

    assert InboxMessage.objects.get(platform_message_id="c1").related_post_id == platform_post.id
    assert InboxMessage.objects.get(platform_message_id="c2").related_post_id is None
    assert InboxMessage.objects.get(platform_message_id="c3").related_post_id is None


@pytest.mark.django_db
def test_a_comment_backlog_is_silent_on_an_account_that_already_has_dms(connected_account):
    """The day comment polling starts working, an account with months of DM
    history is not 'first sync' — but its whole comment backlog arrives at once
    and would notify every owner and manager for each one."""
    InboxMessage.objects.create(
        workspace=connected_account.workspace,
        social_account=connected_account,
        platform_message_id="old-dm",
        message_type=InboxMessage.MessageType.DM,
        sender_name="Someone",
        body="an old dm",
        received_at=timezone.now() - timedelta(days=30),
    )

    with patch("apps.inbox.tasks.get_provider") as get_provider:
        provider = get_provider.return_value
        provider.get_messages.return_value = [_comment("old-comment", minutes_ago=1440)]
        with patch.object(InboxSyncEngine, "_notify_new_message") as notify_new:
            InboxSyncEngine().sync_all()

        assert InboxMessage.objects.filter(platform_message_id="old-comment").exists()
        notify_new.assert_not_called()

        # Once comments are established, a genuinely new one notifies.
        provider.get_messages.return_value = [_comment("new-comment", minutes_ago=0)]
        with patch.object(InboxSyncEngine, "_notify_new_message") as notify_new:
            InboxSyncEngine().sync_all()
        notify_new.assert_called_once()


# ---------------------------------------------------------------------------
# Quota discipline
#
# YouTube's Data API grants 10,000 units a DAY to the whole OAuth client, so
# what the inbox spends is taken from the same pool analytics and reconnecting
# draw on (uploads have a bucket of their own). Every test below pins one of the three things that stop
# this poller spending it: the breaker, the per-platform floor, and the sweep
# that makes the floor affordable.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_quota_blocked_credential_is_not_polled(workspace):
    """A block already recorded means no request at all — not one to be refused."""
    from apps.common.quota import credential_key, trip_quota_block

    _youtube_account(workspace)
    provider = MagicMock()
    provider.credentials = {"client_id": "shared-client"}
    trip_quota_block(
        "youtube",
        credential_key(provider.credentials),
        "data",
        until=timezone.now() + timedelta(hours=6),
        reason="daily quota exhausted",
    )

    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    provider.get_messages.assert_not_called()


@pytest.mark.django_db
def test_a_quota_refusal_trips_the_block_for_the_next_run(workspace):
    """One refusal has to stand the whole pass down, not just this account.

    Without it the next cycle five minutes later spends another doomed request,
    which is how one exhausted hour used to become an exhausted day.
    """
    from apps.analytics.models import ProviderQuotaBlock

    _youtube_account(workspace)
    resets_at = timezone.now() + timedelta(hours=9)
    provider = MagicMock()
    provider.credentials = {"client_id": "shared-client"}
    provider.get_messages.side_effect = QuotaExceededError(
        "YouTube daily quota exhausted (data API)",
        resets_at=resets_at,
        quota_scope="data",
        status_code=403,
    )

    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    block = ProviderQuotaBlock.objects.get(platform="youtube", quota_scope="data")
    assert block.blocked_until == resets_at


@pytest.mark.django_db
def test_a_quota_refusal_does_not_stamp_the_poll_clock(workspace):
    """The breaker holds this account back now; the poll clock must not outlast it."""
    account = _youtube_account(workspace)
    provider = MagicMock()
    provider.credentials = {"client_id": "shared-client"}
    provider.get_messages.side_effect = QuotaExceededError(
        "exhausted", resets_at=timezone.now() + timedelta(hours=2), quota_scope="data", status_code=403
    )

    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    account.refresh_from_db()
    assert account.inbox_last_polled_at is None


@pytest.mark.django_db
def test_youtube_is_not_repolled_inside_its_platform_floor(workspace):
    """The cycle runs every 5 minutes; YouTube opts out of most of those passes."""
    account = _youtube_account(workspace)
    account.inbox_last_polled_at = timezone.now() - timedelta(minutes=10)
    account.inbox_last_deep_sweep_at = timezone.now()
    account.save(update_fields=["inbox_last_polled_at", "inbox_last_deep_sweep_at"])

    provider = MagicMock()
    provider.credentials = {}
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    provider.get_messages.assert_not_called()


@pytest.mark.django_db
def test_youtube_is_polled_once_past_its_platform_floor(workspace):
    account = _youtube_account(workspace)
    account.inbox_last_polled_at = timezone.now() - timedelta(minutes=45)
    account.inbox_last_deep_sweep_at = timezone.now()
    account.save(update_fields=["inbox_last_polled_at", "inbox_last_deep_sweep_at"])

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    provider.get_messages.assert_called_once()
    account.refresh_from_db()
    assert account.inbox_last_polled_at > timezone.now() - timedelta(minutes=1)


@pytest.mark.django_db
def test_a_platform_without_a_floor_keeps_the_five_minute_cadence(connected_account):
    """The floor is YouTube's problem, not everyone's."""
    connected_account.inbox_last_polled_at = timezone.now() - timedelta(minutes=5)
    connected_account.save(update_fields=["inbox_last_polled_at"])

    with patch("apps.inbox.tasks.get_provider") as get_provider:
        get_provider.return_value.get_messages.return_value = []
        InboxSyncEngine().sync_all()

    get_provider.return_value.get_messages.assert_called_once()


def test_any_platform_can_set_a_floor_from_the_environment():
    from config.settings.base import inbox_platform_min_poll_seconds

    floors = inbox_platform_min_poll_seconds(
        {
            "INBOX_LINKEDIN_COMPANY_MIN_POLL_SECONDS": "31536000",
            "INBOX_YOUTUBE_MIN_POLL_SECONDS": "3600",
            "INBOX_DEEP_SWEEP_SECONDS": "60",
        }
    )

    assert floors == {"youtube": 3600, "linkedin_company": 31536000}


def test_youtube_keeps_its_default_floor_and_zero_removes_it():
    from config.settings.base import inbox_platform_min_poll_seconds

    assert inbox_platform_min_poll_seconds({}) == {"youtube": 1800}
    assert inbox_platform_min_poll_seconds({"INBOX_YOUTUBE_MIN_POLL_SECONDS": "0"}) == {"youtube": 0}


def _linkedin_company_account(workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_company",
        account_platform_id="li-sync-1",
        account_name="LinkedIn Sync Test",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


@pytest.mark.django_db
def test_a_configured_platform_is_not_repolled_inside_its_floor(workspace, settings):
    settings.INBOX_PLATFORM_MIN_POLL_SECONDS = {"youtube": 1800, "linkedin_company": 365 * 24 * 60 * 60}
    account = _linkedin_company_account(workspace)
    account.inbox_last_polled_at = timezone.now() - timedelta(days=30)
    account.save(update_fields=["inbox_last_polled_at"])

    provider = MagicMock()
    provider.credentials = {}
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    provider.get_messages.assert_not_called()


@pytest.mark.django_db
def test_a_configured_platform_is_polled_once_past_its_floor(workspace, settings):
    settings.INBOX_PLATFORM_MIN_POLL_SECONDS = {"youtube": 1800, "linkedin_company": 3600}
    account = _linkedin_company_account(workspace)
    account.inbox_last_polled_at = timezone.now() - timedelta(hours=2)
    account.save(update_fields=["inbox_last_polled_at"])

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    provider.get_messages.assert_called_once()


@pytest.mark.django_db
def test_a_stale_account_gets_the_deep_sweep(workspace):
    """The weekly walk is what finds a reply older than the routine poll's lookback."""
    account = _youtube_account(workspace)
    account.inbox_last_deep_sweep_at = timezone.now() - timedelta(days=8)
    account.save(update_fields=["inbox_last_deep_sweep_at"])

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    assert provider.get_messages.call_args.kwargs["deep"] is True
    account.refresh_from_db()
    assert account.inbox_last_deep_sweep_at > timezone.now() - timedelta(minutes=1)


@pytest.mark.django_db
def test_a_freshly_connected_account_does_not_immediately_deep_sweep(workspace):
    """The first poll already imports the backlog; sweeping would buy the same pages twice."""
    account = _youtube_account(workspace)
    assert account.inbox_last_deep_sweep_at is None

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    assert provider.get_messages.call_args.kwargs["deep"] is False
    account.refresh_from_db()
    # The first successful poll is the baseline the weekly clock runs from.
    assert account.inbox_last_deep_sweep_at is not None


@pytest.mark.django_db
def test_a_recently_swept_account_is_not_swept_again(workspace):
    account = _youtube_account(workspace)
    account.inbox_last_deep_sweep_at = timezone.now() - timedelta(days=2)
    account.save(update_fields=["inbox_last_deep_sweep_at"])

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    assert provider.get_messages.call_args.kwargs["deep"] is False


def _stored_comment(account, message_id, *, parent_id=None):
    extra = {"video_id": "vid1", "comment_id": message_id}
    if parent_id:
        extra["parent_id"] = parent_id
    return InboxMessage.objects.create(
        workspace=account.workspace,
        social_account=account,
        platform_message_id=message_id,
        sender_name="Viewer",
        body="hi",
        message_type=InboxMessage.MessageType.COMMENT,
        received_at=timezone.now() - timedelta(hours=1),
        extra=extra,
    )


@pytest.mark.django_db
def test_youtube_routine_poll_uses_the_stored_channel_and_skips_reply_counts(workspace):
    """The stored id spares a ``channels.list`` unit per poll; only history walks need reply counts."""
    account = _youtube_account(workspace)
    account.inbox_last_deep_sweep_at = timezone.now() - timedelta(days=2)
    account.save(update_fields=["inbox_last_deep_sweep_at"])
    _stored_comment(account, "top-1")

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    kwargs = provider.get_messages.call_args.kwargs
    assert kwargs["channel_id"] == "yt-sync-1"
    assert kwargs["since"] is not None
    assert "stored_reply_counts" not in kwargs


@pytest.mark.django_db
def test_youtube_poll_without_a_stored_channel_falls_back_to_the_lookup(workspace):
    account = _youtube_account(workspace)
    SocialAccount.objects.filter(pk=account.pk).update(account_platform_id="")

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    assert "channel_id" not in provider.get_messages.call_args.kwargs


@pytest.mark.django_db
def test_youtube_deep_sweep_looks_up_stored_reply_counts_per_thread(workspace, settings):
    # Swept moments ago, in this calendar month, with a zero-length interval:
    # due again, but not the month's full walk — whatever day the suite runs.
    settings.INBOX_DEEP_SWEEP_SECONDS = 0
    account = _youtube_account(workspace)
    account.inbox_last_deep_sweep_at = timezone.now()
    account.save(update_fields=["inbox_last_deep_sweep_at"])
    _stored_comment(account, "top-1")
    _stored_comment(account, "reply-1", parent_id="top-1")
    _stored_comment(account, "reply-2", parent_id="top-1")
    _stored_comment(account, "reply-3", parent_id="top-2")
    _stored_comment(account, "reply-4", parent_id="top-3")

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    kwargs = provider.get_messages.call_args.kwargs
    assert kwargs["deep"] is True
    # Only the threads asked about, so a capped walk never loads the whole history.
    assert kwargs["stored_reply_counts"](["top-1", "top-2", "unknown"]) == {"top-1": 2, "top-2": 1}


@pytest.mark.django_db
def test_the_first_deep_sweep_of_a_month_fetches_every_reply_thread(workspace):
    """A count can match by coincidence (one deleted, one added); a monthly full walk bounds that."""
    account = _youtube_account(workspace)
    account.inbox_last_deep_sweep_at = timezone.now() - timedelta(days=40)
    account.save(update_fields=["inbox_last_deep_sweep_at"])

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    kwargs = provider.get_messages.call_args.kwargs
    assert kwargs["deep"] is True
    assert "stored_reply_counts" not in kwargs


def _last_month_sweep():
    """A completed sweep on the 15th of an earlier calendar month, whatever today is."""
    return (timezone.now() - timedelta(days=40)).replace(day=15, hour=12, minute=0, second=0, microsecond=0)


@pytest.mark.django_db
def test_the_full_walk_reaches_back_to_the_last_full_walk(workspace):
    """Keeping last week's cutoff would fetch a skipped reply only to drop it as too old."""
    account = _youtube_account(workspace)
    last_sweep = _last_month_sweep()
    account.inbox_last_deep_sweep_at = last_sweep
    account.save(update_fields=["inbox_last_deep_sweep_at"])

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    assert provider.get_messages.call_args.kwargs["since"] == last_sweep.replace(day=1, hour=0)


@pytest.mark.django_db
def test_a_reply_skipped_by_a_weekly_sweep_is_recovered_by_the_monthly_walk(workspace):
    """End to end: one reply deleted upstream and one added keeps the count equal.

    The weekly sweep skips the thread on that count, and the reply, posted
    before the last sweep, would fall behind its cutoff for good. The month's
    full walk must both fetch the thread and still emit the reply.
    """
    from providers.youtube import YouTubeProvider

    account = _youtube_account(workspace)
    last_sweep = _last_month_sweep()
    account.inbox_last_deep_sweep_at = last_sweep
    account.save(update_fields=["inbox_last_deep_sweep_at"])
    _stored_comment(account, "top-old")
    # Three stored replies, one of them since deleted on YouTube: the count still reads 3.
    for reply_id in ("embedded", "kept", "deleted-upstream"):
        _stored_comment(account, reply_id, parent_id="top-old")

    def stamp(moment):
        return moment.isoformat().replace("+00:00", "Z")

    def reply(reply_id, published):
        return {
            "id": reply_id,
            "snippet": {
                "publishedAt": stamp(published),
                "authorDisplayName": f"author-{reply_id}",
                "textDisplay": f"text-{reply_id}",
                "authorChannelId": {"value": f"chan-{reply_id}"},
            },
        }

    thread = {
        "snippet": {
            "totalReplyCount": 3,
            "topLevelComment": {
                "id": "top-old",
                "snippet": {
                    "publishedAt": stamp(last_sweep - timedelta(days=60)),
                    "videoId": "vid1",
                    "authorDisplayName": "viewer",
                    "textDisplay": "first",
                    "authorChannelId": {"value": "chan-top"},
                },
            },
        },
        "replies": {"comments": [reply("embedded", last_sweep - timedelta(days=30))]},
    }
    missed = reply("missed", last_sweep - timedelta(days=2))

    def respond(method, url, **kwargs):
        response = MagicMock()
        if url.endswith("/commentThreads"):
            response.json.return_value = {"items": [thread]}
        else:
            response.json.return_value = {
                "items": [reply("embedded", last_sweep - timedelta(days=30)), reply("kept", last_sweep), missed]
            }
        return response

    provider = YouTubeProvider()
    with (
        patch.object(YouTubeProvider, "_request", side_effect=respond) as request,
        patch("apps.inbox.tasks.get_provider", return_value=provider),
    ):
        InboxSyncEngine().sync_all()

    assert any(call.args[1].endswith("/comments") for call in request.call_args_list)
    recovered = InboxMessage.objects.get(social_account=account, platform_message_id="missed")
    assert recovered.extra["parent_id"] == "top-old"


@pytest.mark.django_db
def test_youtube_initial_history_call_also_saves_quota(workspace):
    """The resumable first import is the second call of a cycle; it must not lose either saving."""
    account = _youtube_account(workspace)
    account.inbox_initial_backfill_cursor = "history-page-3"
    account.save(update_fields=["inbox_initial_backfill_cursor"])
    _stored_comment(account, "top-1")

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = YouTubeMessageBatch([])
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    routine, history = (call.kwargs for call in provider.get_messages.call_args_list)
    assert routine["since"] is not None
    assert routine["channel_id"] == "yt-sync-1"
    assert "stored_reply_counts" not in routine
    assert history["since"] is None
    assert history["page_token"] == "history-page-3"
    assert history["channel_id"] == "yt-sync-1"
    # No later walk reaches back far enough to recover a skip made here.
    assert "stored_reply_counts" not in history


@pytest.mark.django_db
def test_the_cycle_reports_what_it_spent(workspace, caplog):
    """The number that answers "how close is today to 10,000?".

    Per-cycle rather than per-account because a cycle figure multiplies
    straight out to a daily one — which is the question worth asking, and the
    one nobody could answer the first time the budget ran dry.
    """
    import logging

    _youtube_account(workspace)
    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    provider.last_call_quota_units = 4

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        caplog.at_level(logging.INFO, logger="apps.inbox.tasks"),
    ):
        InboxSyncEngine().sync_all()

    assert any("Inbox cycle quota spend: youtube=4" in r.getMessage() for r in caplog.records), [
        r.getMessage() for r in caplog.records
    ]


@pytest.mark.django_db
def test_a_platform_that_meters_nothing_is_not_tallied(connected_account, caplog):
    """last_call_quota_units defaults to 0, so those platforms never appear."""
    import logging

    with (
        patch("apps.inbox.tasks.get_provider") as get_provider,
        caplog.at_level(logging.INFO, logger="apps.inbox.tasks"),
    ):
        get_provider.return_value.get_messages.return_value = []
        get_provider.return_value.last_call_quota_units = 0
        InboxSyncEngine().sync_all()

    assert not any("quota spend" in r.getMessage() for r in caplog.records)


@pytest.mark.django_db
def test_a_failed_poll_still_counts_the_pages_it_bought(workspace, caplog):
    """A tally that only counted successes would understate the worst days."""
    import logging

    _youtube_account(workspace)
    provider = MagicMock()
    provider.credentials = {}
    provider.last_call_quota_units = 3
    provider.get_messages.side_effect = APIError("boom", status_code=500)

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        caplog.at_level(logging.INFO, logger="apps.inbox.tasks"),
    ):
        InboxSyncEngine().sync_all()

    assert any("Inbox cycle quota spend: youtube=3" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# What the routine poll's early exit leaves behind
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_sweep_asks_for_the_window_since_the_last_sweep(workspace):
    """Not the newest-message high-water mark, which would filter out its whole point.

    The sweep exists to find what the early exit missed — by definition older
    than the newest message already imported. Reusing that mark as ``since``
    would drop exactly those messages after paying for the full walk, leaving a
    sweep that costs everything and recovers nothing.
    """
    account = _youtube_account(workspace)
    swept_at = timezone.now() - timedelta(days=8)
    account.inbox_last_deep_sweep_at = swept_at
    account.save(update_fields=["inbox_last_deep_sweep_at"])
    # A message imported an hour ago, so the high-water mark is recent.
    InboxMessage.objects.create(
        workspace=workspace,
        social_account=account,
        platform_message_id="recent",
        sender_name="S",
        body="hi",
        message_type=InboxMessage.MessageType.COMMENT,
        received_at=timezone.now() - timedelta(hours=1),
    )

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    kwargs = provider.get_messages.call_args.kwargs
    assert kwargs["deep"] is True
    assert kwargs["since"] == swept_at


@pytest.mark.django_db
def test_only_one_account_is_swept_per_cycle(workspace):
    """Every account's baseline is stamped within a few cycles, so they come due together."""
    stale = timezone.now() - timedelta(days=8)
    for i in range(3):
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="youtube",
            account_platform_id=f"yt-sweep-{i}",
            account_name=f"Channel {i}",
            oauth_access_token="tok",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
            inbox_last_deep_sweep_at=stale,
        )
        assert account.pk

    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.return_value = []
    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    deep_calls = [c for c in provider.get_messages.call_args_list if c.kwargs.get("deep")]
    assert len(deep_calls) == 1
    assert provider.get_messages.call_count == 3


@pytest.mark.django_db
def test_a_failed_first_poll_does_not_claim_the_history_was_swept(workspace):
    """Otherwise a brand-new account waits a week for a walk that never happened."""
    account = _youtube_account(workspace)
    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.side_effect = APIError("boom", status_code=500)

    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()

    account.refresh_from_db()
    assert account.inbox_last_deep_sweep_at is None
    # The poll clock still moves: a platform that just refused us is not one to
    # come back to in five minutes.
    assert account.inbox_last_polled_at is not None


@pytest.mark.django_db
def test_the_tally_is_reset_once_per_account_not_once_per_call(workspace, caplog):
    """The provider accumulates across calls, so the inbox owns the reset.

    Accumulating is what keeps the YouTube auth retry's first attempt in the
    tally — a per-call counter reported only the retry. The cost of that is
    that somebody has to zero it, and the unit of work is one account's poll.
    """
    import logging

    for i in range(2):
        SocialAccount.objects.create(
            workspace=workspace,
            platform="youtube",
            account_platform_id=f"yt-tally-{i}",
            account_name=f"Channel {i}",
            oauth_access_token="tok",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
            inbox_last_deep_sweep_at=timezone.now(),
        )

    provider = MagicMock()
    provider.credentials = {}
    provider.last_call_quota_units = 0
    provider.get_messages.side_effect = lambda **kw: (
        setattr(provider, "last_call_quota_units", provider.last_call_quota_units + 3),
        [],
    )[1]
    provider.reset_quota_counter.side_effect = lambda: setattr(provider, "last_call_quota_units", 0)

    with (
        patch("apps.inbox.tasks.get_provider", return_value=provider),
        caplog.at_level(logging.INFO, logger="apps.inbox.tasks"),
    ):
        InboxSyncEngine().sync_all()

    records = caplog.records

    # 3 + 3, not 3 + 6: without the per-account reset the second account would
    # be billed for the first one's pages as well.
    assert any("Inbox cycle quota spend: youtube=6" in r.getMessage() for r in records), [
        r.getMessage() for r in records
    ]


@pytest.mark.django_db
def test_first_youtube_import_continues_after_page_cap(workspace):
    account = _youtube_account(workspace)
    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.side_effect = [
        YouTubeMessageBatch([_comment("recent")], "page-6"),
        YouTubeMessageBatch([]),  # Routine poll on the next cycle.
        YouTubeMessageBatch([_comment("older", minutes_ago=10_000)]),
    ]

    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()
        account.refresh_from_db()
        assert account.inbox_initial_backfill_cursor == "page-6"
        assert account.inbox_last_deep_sweep_at is None
        started_at = account.inbox_initial_backfill_started_at

        account.inbox_last_polled_at = timezone.now() - timedelta(minutes=45)
        account.save(update_fields=["inbox_last_polled_at"])
        with patch.object(InboxSyncEngine, "_notify_new_message") as notify_new:
            InboxSyncEngine().sync_all()
        notify_new.assert_not_called()

    account.refresh_from_db()
    assert provider.get_messages.call_args_list[2].kwargs["page_token"] == "page-6"
    assert InboxMessage.objects.filter(social_account=account, platform_message_id="older").exists()
    assert account.inbox_initial_backfill_cursor == ""
    assert account.inbox_last_deep_sweep_at == started_at


@pytest.mark.django_db
def test_deep_sweep_resumes_and_uses_start_as_next_baseline(workspace):
    account = _youtube_account(workspace)
    previous_baseline = timezone.now() - timedelta(days=8)
    account.inbox_last_deep_sweep_at = previous_baseline
    account.save(update_fields=["inbox_last_deep_sweep_at"])
    provider = MagicMock()
    provider.credentials = {}
    provider.get_messages.side_effect = [YouTubeMessageBatch([], "page-51"), YouTubeMessageBatch([])]

    with patch("apps.inbox.tasks.get_provider", return_value=provider):
        InboxSyncEngine().sync_all()
        account.refresh_from_db()
        assert account.inbox_last_deep_sweep_at == previous_baseline
        assert account.inbox_deep_sweep_cursor == "page-51"
        sweep_started_at = account.inbox_deep_sweep_started_at

        account.inbox_last_polled_at = timezone.now() - timedelta(minutes=45)
        account.save(update_fields=["inbox_last_polled_at"])
        InboxSyncEngine().sync_all()

    account.refresh_from_db()
    assert provider.get_messages.call_args_list[1].kwargs["page_token"] == "page-51"
    assert account.inbox_last_deep_sweep_at == sweep_started_at
    assert account.inbox_deep_sweep_cursor == ""
