"""Draft-reply lifecycle in ``apps.inbox.services``.

Covers create / edit / discard / send, the failed-send retry path, and
the SLA auto-resolve side effect — independently of any HTTP surface.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import timedelta
from threading import Event
from unittest.mock import patch

import pytest
from django.db import connection, connections
from django.utils import timezone

from apps.inbox import services
from apps.inbox.models import InboxMessage, InboxReply, InboxSLAConfig
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Svc WS", organization=organization)


@pytest.fixture
def account(db, workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-1",
        account_name="Page",
        oauth_access_token="tok",
    )


@pytest.fixture
def message(db, account):
    return InboxMessage.objects.create(
        workspace=account.workspace,
        social_account=account,
        platform_message_id="pm-1",
        message_type=InboxMessage.MessageType.COMMENT,
        sender_name="Ada",
        sender_handle="ada",
        body="hi?",
        received_at=timezone.now() - timedelta(hours=1),
    )


def test_create_reply_draft_starts_in_draft(message, user):
    reply = services.create_reply_draft(message=message, body="  hello  ", author=user)
    assert reply.status == InboxReply.Status.DRAFT
    assert reply.body == "hello"  # trimmed
    assert reply.sent_at is None
    assert reply.author == user


def test_create_reply_draft_rejects_blank(message):
    with pytest.raises(ValueError):
        services.create_reply_draft(message=message, body="   ")


def test_update_reply_draft_changes_body(message):
    reply = services.create_reply_draft(message=message, body="v1")
    services.update_reply_draft(reply, body="v2")
    reply.refresh_from_db()
    assert reply.body == "v2"


def test_update_rejects_sent_reply(message):
    reply = services.create_reply_draft(message=message, body="v1")
    reply.status = InboxReply.Status.SENT
    reply.save(update_fields=["status"])
    with pytest.raises(services.ReplyStateError):
        services.update_reply_draft(reply, body="v2")


def test_discard_removes_draft(message):
    reply = services.create_reply_draft(message=message, body="bye")
    services.discard_reply_draft(reply)
    assert not InboxReply.objects.filter(pk=reply.pk).exists()


def test_discard_rejects_sent_reply(message):
    reply = services.create_reply_draft(message=message, body="v1")
    reply.status = InboxReply.Status.SENT
    reply.save(update_fields=["status"])
    with pytest.raises(services.ReplyStateError):
        services.discard_reply_draft(reply)


def test_send_reply_now_success(message, user):
    reply = services.create_reply_draft(message=message, body="answer", author=user)
    with patch("apps.inbox.services._dispatch_to_platform", return_value="plat-123"):
        services.send_reply_now(reply)
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    assert reply.platform_reply_id == "plat-123"
    assert reply.sent_at is not None


def test_send_reply_now_failure_marks_failed_and_reraises(message):
    reply = services.create_reply_draft(message=message, body="answer")
    with (
        patch("apps.inbox.services._dispatch_to_platform", side_effect=RuntimeError("nope")),
        pytest.raises(RuntimeError),
    ):
        services.send_reply_now(reply)
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.FAILED
    assert reply.send_error  # human-readable reason recorded
    assert reply.sent_at is None


def test_failed_reply_can_be_retried(message):
    reply = services.create_reply_draft(message=message, body="answer")
    with (
        patch("apps.inbox.services._dispatch_to_platform", side_effect=RuntimeError("nope")),
        pytest.raises(RuntimeError),
    ):
        services.send_reply_now(reply)
    with patch("apps.inbox.services._dispatch_to_platform", return_value="ok-1"):
        services.send_reply_now(reply)
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    assert reply.send_error == ""
    assert reply.platform_reply_id == "ok-1"


def test_provider_without_reply_api_records_locally(message):
    reply = services.create_reply_draft(message=message, body="answer")
    with patch("apps.inbox.services._dispatch_to_platform", side_effect=NotImplementedError):
        services.send_reply_now(reply)
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    assert reply.platform_reply_id == ""


def test_send_applies_sla_auto_resolve(message):
    InboxSLAConfig.objects.create(workspace=message.workspace, is_active=True, auto_resolve_on_reply=True)
    reply = services.create_reply_draft(message=message, body="answer")
    with patch("apps.inbox.services._dispatch_to_platform", return_value="x"):
        services.send_reply_now(reply)
    message.refresh_from_db()
    assert message.status == InboxMessage.Status.RESOLVED


def test_send_without_sla_moves_unread_to_open(message):
    assert message.status == InboxMessage.Status.UNREAD
    reply = services.create_reply_draft(message=message, body="answer")
    with patch("apps.inbox.services._dispatch_to_platform", return_value="x"):
        services.send_reply_now(reply)
    message.refresh_from_db()
    assert message.status == InboxMessage.Status.OPEN


def test_send_reply_convenience_removes_failed_row(message):
    with (
        patch("apps.inbox.services._dispatch_to_platform", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        services.send_reply(message=message, body="answer")
    assert InboxReply.objects.filter(inbox_message=message).count() == 0


@pytest.mark.parametrize("operation", ["send", "edit", "discard"])
def test_stale_draft_cannot_change_sent_reply(message, operation):
    reply = services.create_reply_draft(message=message, body="answer")
    stale_reply = InboxReply.objects.get(pk=reply.pk)
    with patch("apps.inbox.services._dispatch_to_platform", return_value="sent-1") as dispatch:
        services.send_reply_now(reply)
        with pytest.raises(services.ReplyStateError):
            if operation == "send":
                services.send_reply_now(stale_reply)
            elif operation == "edit":
                services.update_reply_draft(stale_reply, body="different answer")
            else:
                services.discard_reply_draft(stale_reply)
    dispatch.assert_called_once()
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    assert reply.body == "answer"


def test_send_uses_latest_saved_draft(message):
    reply = services.create_reply_draft(message=message, body="original")
    latest = InboxReply.objects.get(pk=reply.pk)
    services.update_reply_draft(latest, body="approved answer")
    with patch("apps.inbox.services._dispatch_to_platform", return_value="sent-1") as dispatch:
        services.send_reply_now(reply)
    assert dispatch.call_args.args[1] == "approved answer"
    assert reply.body == "approved answer"


def test_discarded_reply_cannot_be_sent_from_stale_instance(message):
    reply = services.create_reply_draft(message=message, body="answer")
    services.discard_reply_draft(InboxReply.objects.get(pk=reply.pk))
    with (
        patch("apps.inbox.services._dispatch_to_platform") as dispatch,
        pytest.raises(services.ReplyStateError, match="discarded"),
    ):
        services.send_reply_now(reply)
    dispatch.assert_not_called()


def test_sla_failure_does_not_make_delivered_reply_sendable_again(message):
    reply = services.create_reply_draft(message=message, body="answer")
    with (
        patch("apps.inbox.services._dispatch_to_platform", return_value="sent-1") as dispatch,
        patch("apps.inbox.services._apply_post_send_side_effects", side_effect=RuntimeError("SLA failed")),
    ):
        assert services.send_reply_now(reply).status == InboxReply.Status.SENT
        reply.refresh_from_db()
        assert reply.status == InboxReply.Status.SENT
        assert reply.platform_reply_id == "sent-1"
        with pytest.raises(services.ReplyStateError):
            services.send_reply_now(reply)
    dispatch.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_concurrent_sends_deliver_draft_once(message):
    if not connection.features.has_select_for_update:
        pytest.skip("Requires database row locks")
    reply = services.create_reply_draft(message=message, body="answer")
    stale_reply = InboxReply.objects.get(pk=reply.pk)
    dispatch_started = Event()
    release_dispatch = Event()
    second_started = Event()

    def dispatch(message, body):
        dispatch_started.set()
        assert release_dispatch.wait(timeout=10)
        return "sent-once"

    def send(instance, started=None):
        try:
            if started is not None:
                started.set()
            return services.send_reply_now(instance).status
        finally:
            connections.close_all()

    with patch("apps.inbox.services._dispatch_to_platform", side_effect=dispatch) as mocked_dispatch:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(send, reply)
            try:
                assert dispatch_started.wait(timeout=10)
                second = executor.submit(send, stale_reply, second_started)
                assert second_started.wait(timeout=10)
                with pytest.raises(TimeoutError):
                    second.result(timeout=0.2)
            finally:
                release_dispatch.set()
            assert first.result(timeout=10) == InboxReply.Status.SENT
            with pytest.raises(services.ReplyStateError, match="cannot be sent again"):
                second.result(timeout=10)
        mocked_dispatch.assert_called_once()
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    assert reply.platform_reply_id == "sent-once"
