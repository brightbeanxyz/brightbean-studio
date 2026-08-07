"""The inbox sync engine suppresses first-sync history but never the first real message."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.inbox.models import InboxMessage
from apps.inbox.tasks import InboxSyncEngine
from apps.social_accounts.models import SocialAccount


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
