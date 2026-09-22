"""MCP inbox tools: list / get messages, draft / send / discard replies."""

from __future__ import annotations

import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.inbox.models import InboxMessage, InboxReply
from apps.mcp.handlers import _send_reply
from apps.mcp.protocol import INVALID_PARAMS, JsonRpcError
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership
from providers.exceptions import RateLimitError, TokenExpiredError

MCP_URL = "/api/v1/mcp/"


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


def _rpc(name: str, arguments: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def _call(client: Client, name: str, arguments: dict):
    r = client.post(MCP_URL, data=json.dumps(_rpc(name, arguments)), content_type="application/json")
    return r.status_code, r.json()


def _result_json(body: dict) -> dict:
    return json.loads(body["result"]["content"][0]["text"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="mcp-inbox@example.com", password="x", name="MCP Inbox", tos_accepted_at=timezone.now()
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="WS", organization=organization)


@pytest.fixture
def memberships(db, user, organization, workspace):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
    return WorkspaceMembership.objects.create(
        user=user, workspace=workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )


@pytest.fixture
def account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-1",
        account_name="Page",
        connection_status="connected",
        oauth_access_token="tok",
    )


@pytest.fixture
def other_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-2",
        account_name="Page 2",
        connection_status="connected",
        oauth_access_token="tok2",
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


@pytest.fixture
def full_client(db, user, memberships, workspace, account):
    key = services.issue_api_key(
        workspace=workspace,
        social_accounts=[account],
        issued_by=user,
        name="full",
        permissions=list(PERMISSION_KEYS),
    )
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {key.plaintext_token}")


@pytest.fixture
def draft_only_client(db, user, memberships, workspace, account):
    key = services.issue_api_key(
        workspace=workspace,
        social_accounts=[account],
        issued_by=user,
        name="draft-only",
        permissions=["use_inbox"],
    )
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {key.plaintext_token}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInboxReadTools:
    def test_list_inbox_messages(self, full_client, message):
        InboxReply.objects.create(inbox_message=message, body="a draft")
        _s, body = _call(full_client, "list_inbox_messages", {})
        data = _result_json(body)
        assert len(data["messages"]) == 1
        assert data["messages"][0]["replies"][0]["body"] == "a draft"

    def test_list_excludes_non_allowlisted_account(self, full_client, message, other_account):
        InboxMessage.objects.create(
            workspace=other_account.workspace,
            social_account=other_account,
            platform_message_id="pm-x",
            message_type=InboxMessage.MessageType.COMMENT,
            sender_name="X",
            body="?",
            received_at=timezone.now(),
        )
        _s, body = _call(full_client, "list_inbox_messages", {})
        data = _result_json(body)
        assert {m["id"] for m in data["messages"]} == {str(message.id)}

    def test_get_inbox_message(self, full_client, message):
        _s, body = _call(full_client, "get_inbox_message", {"message_id": str(message.id)})
        assert _result_json(body)["id"] == str(message.id)

    def test_get_unknown_message_errors(self, full_client):
        import uuid

        _s, body = _call(full_client, "get_inbox_message", {"message_id": str(uuid.uuid4())})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "not found" in body["error"]["message"].lower()


@pytest.mark.django_db
class TestInboxReplyTools:
    def test_create_reply_draft(self, full_client, message):
        _s, body = _call(full_client, "create_reply_draft", {"message_id": str(message.id), "body": "hi"})
        data = _result_json(body)
        assert data["status"] == "draft"
        assert InboxReply.objects.get(id=data["id"]).body == "hi"

    def test_create_reply_draft_needs_use_inbox(self, db, user, memberships, workspace, account, message):
        key = services.issue_api_key(
            workspace=workspace,
            social_accounts=[account],
            issued_by=user,
            name="none",
            permissions=["view_analytics"],
        )
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {key.plaintext_token}")
        _s, body = _call(c, "create_reply_draft", {"message_id": str(message.id), "body": "hi"})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "permission denied" in body["error"]["message"].lower()

    def test_update_reply_draft(self, full_client, message):
        reply = InboxReply.objects.create(inbox_message=message, body="v1")
        _s, body = _call(full_client, "update_reply_draft", {"reply_id": str(reply.id), "body": "v2"})
        assert _result_json(body)["body"] == "v2"

    def test_discard_reply_draft(self, full_client, message):
        reply = InboxReply.objects.create(inbox_message=message, body="scrap")
        _s, body = _call(full_client, "discard_reply_draft", {"reply_id": str(reply.id)})
        assert _result_json(body)["discarded"] is True
        assert not InboxReply.objects.filter(pk=reply.pk).exists()

    def test_send_reply_with_reply_id(self, full_client, message):
        reply = InboxReply.objects.create(inbox_message=message, body="ready")
        with patch("apps.inbox.services._dispatch_to_platform", return_value="plat-1") as dispatch:
            _s, body = _call(full_client, "send_reply", {"reply_id": str(reply.id)})
        assert _result_json(body)["status"] == "sent"
        dispatch.assert_called_once_with(message, "ready")
        assert message.replies.count() == 1

    def test_send_reply_create_and_send(self, full_client, message):
        with patch("apps.inbox.services._dispatch_to_platform", return_value="plat-2") as dispatch:
            _s, body = _call(full_client, "send_reply", {"message_id": str(message.id), "body": "yo"})
        data = _result_json(body)
        assert data["status"] == "sent"
        assert data["platform_reply_id"] == "plat-2"
        dispatch.assert_called_once_with(message, "yo")
        assert message.replies.count() == 1

    @pytest.mark.parametrize("extra_fields", [("message_id",), ("body",), ("message_id", "body")])
    def test_send_reply_rejects_mixed_modes_without_side_effects(self, full_client, message, extra_fields):
        reply = InboxReply.objects.create(inbox_message=message, body="reviewed draft")
        values = {"message_id": str(message.id), "body": "replacement text"}
        arguments = {"reply_id": str(reply.id), **{key: values[key] for key in extra_fields}}

        with patch("apps.inbox.services._dispatch_to_platform") as dispatch:
            _s, body = _call(full_client, "send_reply", arguments)

        assert body["error"]["code"] == INVALID_PARAMS
        dispatch.assert_not_called()
        reply.refresh_from_db()
        assert reply.status == InboxReply.Status.DRAFT
        assert reply.body == "reviewed draft"
        assert message.replies.count() == 1

    @pytest.mark.parametrize("reply_id", ["existing-reply", "", None])
    @pytest.mark.parametrize("extra_fields", [{"message_id": "message"}, {"body": "new text"}])
    def test_send_reply_handler_rejects_mixed_modes_before_resolving_reply(self, reply_id, extra_fields):
        context = {
            "membership": SimpleNamespace(effective_permissions={"reply_from_inbox": True}),
            "api_key": SimpleNamespace(issued_by_id=None),
        }
        with (
            patch("apps.mcp.handlers._get_inbox_reply_for_key") as get_reply,
            patch("apps.mcp.handlers.create_reply_draft") as create,
            patch("apps.mcp.handlers.send_reply_now") as send,
            pytest.raises(JsonRpcError, match="cannot be combined"),
        ):
            _send_reply({"reply_id": reply_id, **extra_fields}, context)

        get_reply.assert_not_called()
        create.assert_not_called()
        send.assert_not_called()

    def test_send_reply_requires_reply_from_inbox(self, draft_only_client, message):
        reply = InboxReply.objects.create(inbox_message=message, body="ready")
        _s, body = _call(draft_only_client, "send_reply", {"reply_id": str(reply.id)})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "permission denied: reply_from_inbox" in body["error"]["message"].lower()

    def test_draft_only_client_can_create_draft(self, draft_only_client, message):
        _s, body = _call(draft_only_client, "create_reply_draft", {"message_id": str(message.id), "body": "d"})
        assert _result_json(body)["status"] == "draft"

    @pytest.mark.parametrize("exception_type", [RuntimeError, RateLimitError, TokenExpiredError])
    @pytest.mark.parametrize("existing_draft", [True, False])
    def test_send_reply_platform_failure_is_reshaped(self, full_client, message, exception_type, existing_draft):
        if existing_draft:
            reply = InboxReply.objects.create(inbox_message=message, body="ready")
            arguments = {"reply_id": str(reply.id)}
        else:
            arguments = {"message_id": str(message.id), "body": "ready"}
        diagnostic = "provider raw JSON with access_token=private-provider-token"
        with patch("apps.inbox.services._dispatch_to_platform", side_effect=exception_type(diagnostic)):
            _s, body = _call(full_client, "send_reply", arguments)
        assert body["error"]["code"] == INVALID_PARAMS
        reply = message.replies.get()
        assert reply.status == InboxReply.Status.FAILED
        assert reply.send_error
        assert body["error"]["message"] == f"Reply not sent: {reply.send_error}"
        assert "private-provider-token" not in json.dumps(body)

    def test_reply_on_foreign_account_is_not_found(self, full_client, other_account):
        m = InboxMessage.objects.create(
            workspace=other_account.workspace,
            social_account=other_account,
            platform_message_id="pm-x",
            message_type=InboxMessage.MessageType.COMMENT,
            sender_name="X",
            body="?",
            received_at=timezone.now(),
        )
        reply = InboxReply.objects.create(inbox_message=m, body="x")
        _s, body = _call(full_client, "update_reply_draft", {"reply_id": str(reply.id), "body": "y"})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "not found" in body["error"]["message"].lower()
