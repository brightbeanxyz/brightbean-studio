"""Reply routing: comments go to the comment edge, DMs to the messaging one.

Also covers the two behaviours that decide whether Meta accepts a reply at all:
tagging a late reply as written by a human, and never recording a reply the
platform refused.
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.inbox.models import InboxMessage, InboxReply
from apps.inbox.views import _send_platform_reply
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Reply WS", organization=organization)


@pytest.fixture
def fb_account(db, workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-1",
        account_name="Test Page",
        oauth_access_token="page-token",
    )


def _message(account, *, message_type, hours_ago=1, extra=None, sender_handle="psid-7"):
    return InboxMessage.objects.create(
        workspace=account.workspace,
        social_account=account,
        platform_message_id="platform-msg-1",
        message_type=message_type,
        sender_name="Marta",
        sender_handle=sender_handle,
        body="Question?",
        extra=extra or {},
        received_at=timezone.now() - timedelta(hours=hours_ago),
    )


def _provider(**overrides):
    provider = MagicMock()
    provider.reply_to_comment.return_value = SimpleNamespace(platform_message_id="c-1")
    provider.reply_to_message.return_value = SimpleNamespace(platform_message_id="m-1")
    for key, value in overrides.items():
        setattr(provider, key, value)
    return provider


def test_comment_goes_to_the_comment_edge(fb_account):
    message = _message(fb_account, message_type=InboxMessage.MessageType.COMMENT)
    provider = _provider()

    with patch("apps.inbox.views.get_provider", return_value=provider):
        assert _send_platform_reply(message, "Thanks!") == "c-1"

    provider.reply_to_comment.assert_called_once()
    provider.reply_to_message.assert_not_called()
    assert provider.reply_to_comment.call_args.kwargs["comment_id"] == "platform-msg-1"


def test_mention_is_treated_as_a_comment(fb_account):
    message = _message(fb_account, message_type=InboxMessage.MessageType.MENTION)
    provider = _provider()

    with patch("apps.inbox.views.get_provider", return_value=provider):
        _send_platform_reply(message, "Thanks for the shout-out")

    provider.reply_to_comment.assert_called_once()


def test_providers_without_a_comment_edge_alias_reply_to_comment():
    """Mastodon, LinkedIn and YouTube answer comments through reply_to_message.

    They implement reply_to_comment as a thin alias so the view can call one
    method unconditionally, rather than the view carrying a per-provider
    fallback.
    """
    from providers.linkedin import LinkedInProvider
    from providers.mastodon import MastodonProvider
    from providers.youtube import YouTubeProvider

    for cls in (MastodonProvider, LinkedInProvider, YouTubeProvider):
        provider = cls({"instance_url": "https://example.social"})
        provider.reply_to_message = MagicMock(return_value=SimpleNamespace(platform_message_id="via-message"))

        result = provider.reply_to_comment("token", "comment-1", "Thanks!", {"k": "v"})

        assert result.platform_message_id == "via-message"
        provider.reply_to_message.assert_called_once_with("token", "comment-1", "Thanks!", {"k": "v"})


def test_a_provider_that_cannot_reply_records_the_reply_locally(client, fb_account, org_owner, user):
    """Losing the platform call must not lose the team's written answer."""
    from apps.members.models import WorkspaceMembership

    WorkspaceMembership.objects.create(
        user=user, workspace=fb_account.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM)
    client.force_login(user)

    with patch("apps.inbox.views._send_platform_reply", side_effect=NotImplementedError):
        response = client.post(
            f"/workspace/{fb_account.workspace_id}/inbox/{message.id}/reply/",
            {"body": "Noted internally"},
        )

    assert response.status_code == 200
    assert "HX-Reply-Failed" not in response
    reply = InboxReply.objects.get(inbox_message=message)
    assert reply.platform_reply_id == ""


def test_the_error_shown_to_users_carries_no_raw_api_text(client, fb_account, org_owner, user):
    """Trace IDs and raw API JSON belong in the log, not on a teammate's screen."""
    from apps.members.models import WorkspaceMembership
    from providers.exceptions import APIError

    WorkspaceMembership.objects.create(
        user=user, workspace=fb_account.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM)
    client.force_login(user)

    raw = 'Facebook API error 401: {"error":{"fbtrace_id":"AFC8u7xsP__NwLs"}}'
    with patch("apps.inbox.views._send_platform_reply", side_effect=APIError(raw, platform="facebook")):
        response = client.post(
            f"/workspace/{fb_account.workspace_id}/inbox/{message.id}/reply/",
            {"body": "This will fail"},
        )

    body = response.content.decode()
    assert "Reply not sent" in body
    assert "fbtrace_id" not in body
    assert "401" not in body


def test_an_expired_connection_gets_a_reconnect_hint(client, fb_account, org_owner, user):
    from apps.members.models import WorkspaceMembership
    from providers.exceptions import TokenExpiredError

    WorkspaceMembership.objects.create(
        user=user, workspace=fb_account.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM)
    client.force_login(user)

    with patch("apps.inbox.views._send_platform_reply", side_effect=TokenExpiredError("expired", platform="facebook")):
        response = client.post(
            f"/workspace/{fb_account.workspace_id}/inbox/{message.id}/reply/",
            {"body": "hi"},
        )

    assert "Reconnect the account" in response.content.decode()


def test_recent_dm_replies_without_the_human_agent_tag(fb_account):
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM, hours_ago=2)
    provider = _provider()

    with patch("apps.inbox.views.get_provider", return_value=provider):
        _send_platform_reply(message, "On it")

    assert provider.reply_to_message.call_args.kwargs["human_agent"] is False


def test_dm_older_than_24_hours_is_tagged_human_agent(fb_account):
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM, hours_ago=30)
    provider = _provider()

    with patch("apps.inbox.views.get_provider", return_value=provider):
        _send_platform_reply(message, "Sorry for the delay")

    assert provider.reply_to_message.call_args.kwargs["human_agent"] is True


def test_sender_handle_is_passed_as_the_recipient(fb_account):
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM, sender_handle="psid-99")
    provider = _provider()

    with patch("apps.inbox.views.get_provider", return_value=provider):
        _send_platform_reply(message, "Hi")

    assert provider.reply_to_message.call_args.kwargs["extra"]["recipient_id"] == "psid-99"


def test_existing_extra_recipient_is_not_overwritten(fb_account):
    message = _message(
        fb_account,
        message_type=InboxMessage.MessageType.DM,
        extra={"recipient_id": "from-payload"},
        sender_handle="psid-99",
    )
    provider = _provider()

    with patch("apps.inbox.views.get_provider", return_value=provider):
        _send_platform_reply(message, "Hi")

    assert provider.reply_to_message.call_args.kwargs["extra"]["recipient_id"] == "from-payload"


def test_failed_send_records_no_reply(client, fb_account, org_owner, user):
    """The thread must never show a reply the customer never received."""
    from apps.members.models import WorkspaceMembership

    WorkspaceMembership.objects.create(
        user=user, workspace=fb_account.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM)
    client.force_login(user)

    with patch("apps.inbox.views._send_platform_reply", side_effect=RuntimeError("Meta said no")):
        response = client.post(
            f"/workspace/{fb_account.workspace_id}/inbox/{message.id}/reply/",
            {"body": "This will fail"},
        )

    assert response.status_code == 200
    assert response["HX-Reply-Failed"] == "1"
    assert b"Reply not sent" in response.content
    assert InboxReply.objects.filter(inbox_message=message).count() == 0
    # Status is untouched, so the message stays in the queue to be answered.
    message.refresh_from_db()
    assert message.status == InboxMessage.Status.UNREAD


def test_successful_send_records_the_reply(client, fb_account, org_owner, user):
    from apps.members.models import WorkspaceMembership

    WorkspaceMembership.objects.create(
        user=user, workspace=fb_account.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    message = _message(fb_account, message_type=InboxMessage.MessageType.DM)
    client.force_login(user)

    with patch("apps.inbox.views._send_platform_reply", return_value="mid.sent"):
        response = client.post(
            f"/workspace/{fb_account.workspace_id}/inbox/{message.id}/reply/",
            {"body": "Happy to help"},
        )

    assert response.status_code == 200
    assert "HX-Reply-Failed" not in response
    reply = InboxReply.objects.get(inbox_message=message)
    assert reply.platform_reply_id == "mid.sent"
