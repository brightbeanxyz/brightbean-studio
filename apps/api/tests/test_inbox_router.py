"""``/api/v1/inbox/*`` — list messages, draft / send / discard replies."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.inbox.models import InboxMessage, InboxReply
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="inbox-agent@example.com",
        password="testpass123",
        name="Inbox Agent",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Inbox Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Inbox WS", organization=organization)


@pytest.fixture
def owner_memberships(db, user, organization, workspace):
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
    """A second account in the same workspace, NOT in the key's allowlist."""
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-2",
        account_name="Page 2",
        connection_status="connected",
        oauth_access_token="tok2",
    )


def _message(account, **kw):
    defaults = dict(
        workspace=account.workspace,
        social_account=account,
        platform_message_id="pm-1",
        message_type=InboxMessage.MessageType.COMMENT,
        sender_name="Ada",
        sender_handle="ada",
        body="hi?",
        received_at=timezone.now() - timedelta(hours=1),
    )
    defaults.update(kw)
    return InboxMessage.objects.create(**defaults)


@pytest.fixture
def message(db, account):
    return _message(account)


@pytest.fixture
def full_key(db, user, owner_memberships, workspace, account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[account],
        issued_by=user,
        name="full",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def draft_only_key(db, user, owner_memberships, workspace, account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[account],
        issued_by=user,
        name="draft-only",
        permissions=["use_inbox"],
    )


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def api(full_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {full_key.plaintext_token}")


@pytest.fixture
def draft_api(draft_only_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {draft_only_key.plaintext_token}")


# ---------------------------------------------------------------------------
# List + read
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListAndRead:
    def test_list_returns_allowlisted_messages_with_replies(self, api, message):
        InboxReply.objects.create(inbox_message=message, body="draft one")
        r = api.get("/api/v1/inbox/")
        assert r.status_code == 200, r.content
        body = r.json()
        assert len(body["messages"]) == 1
        msg = body["messages"][0]
        assert msg["id"] == str(message.id)
        assert msg["replies"][0]["body"] == "draft one"
        assert msg["replies"][0]["status"] == "draft"

    def test_list_hides_messages_on_non_allowlisted_account(self, api, message, other_account):
        _message(other_account, platform_message_id="pm-other")
        r = api.get("/api/v1/inbox/")
        ids = {m["id"] for m in r.json()["messages"]}
        assert ids == {str(message.id)}

    def test_list_status_filter_validates(self, api, message):
        r = api.get("/api/v1/inbox/?status=bogus")
        assert r.status_code == 422

    def test_retrieve_foreign_account_message_is_404(self, api, other_account):
        m = _message(other_account, platform_message_id="pm-other")
        r = api.get(f"/api/v1/inbox/{m.id}")
        assert r.status_code == 404

    def test_list_requires_use_inbox(self, message, user, owner_memberships, workspace, account):
        key = services.issue_api_key(
            workspace=workspace,
            social_accounts=[account],
            issued_by=user,
            name="noperm",
            permissions=["view_analytics"],
        )
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {key.plaintext_token}")
        r = c.get("/api/v1/inbox/")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Draft lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReplyDrafts:
    def test_create_draft(self, api, message):
        r = api.post(
            f"/api/v1/inbox/{message.id}/replies",
            data=json.dumps({"body": "drafted via API"}),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["status"] == "draft"
        assert body["body"] == "drafted via API"
        assert InboxReply.objects.get(id=body["id"]).author_id is not None

    def test_create_and_send(self, api, message):
        from unittest.mock import patch

        with patch("apps.inbox.services._dispatch_to_platform", return_value="plat-1"):
            r = api.post(
                f"/api/v1/inbox/{message.id}/replies",
                data=json.dumps({"body": "send now", "send": True}),
                content_type="application/json",
            )
        assert r.status_code == 201, r.content
        assert r.json()["status"] == "sent"
        assert r.json()["platform_reply_id"] == "plat-1"

    def test_draft_only_key_cannot_send(self, draft_api, message):
        r = draft_api.post(
            f"/api/v1/inbox/{message.id}/replies",
            data=json.dumps({"body": "x", "send": True}),
            content_type="application/json",
        )
        assert r.status_code == 403
        assert InboxReply.objects.count() == 0

    def test_draft_only_key_can_draft(self, draft_api, message):
        r = draft_api.post(
            f"/api/v1/inbox/{message.id}/replies",
            data=json.dumps({"body": "just a draft"}),
            content_type="application/json",
        )
        assert r.status_code == 201

    def test_patch_draft_body(self, api, message):
        reply = InboxReply.objects.create(inbox_message=message, body="v1")
        r = api.patch(
            f"/api/v1/inbox/replies/{reply.id}",
            data=json.dumps({"body": "v2"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        reply.refresh_from_db()
        assert reply.body == "v2"

    def test_patch_sent_reply_conflicts(self, api, message):
        reply = InboxReply.objects.create(inbox_message=message, body="v1", status=InboxReply.Status.SENT)
        r = api.patch(
            f"/api/v1/inbox/replies/{reply.id}",
            data=json.dumps({"body": "v2"}),
            content_type="application/json",
        )
        assert r.status_code == 409

    def test_send_endpoint_delivers(self, api, message):
        from unittest.mock import patch

        reply = InboxReply.objects.create(inbox_message=message, body="ready")
        with patch("apps.inbox.services._dispatch_to_platform", return_value="plat-7"):
            r = api.post(f"/api/v1/inbox/replies/{reply.id}/send")
        assert r.status_code == 200
        assert r.json()["status"] == "sent"

    def test_send_endpoint_platform_failure_is_502(self, api, message):
        from unittest.mock import patch

        reply = InboxReply.objects.create(inbox_message=message, body="ready")
        with patch(
            "apps.inbox.services._dispatch_to_platform", side_effect=RuntimeError("access_token=private-provider-token")
        ):
            r = api.post(f"/api/v1/inbox/replies/{reply.id}/send")
        assert r.status_code == 502
        reply.refresh_from_db()
        assert reply.status == InboxReply.Status.FAILED
        assert r.json()["detail"] == f"Reply not sent: {reply.send_error}"
        assert "private-provider-token" not in r.content.decode()

    def test_delete_draft(self, api, message):
        reply = InboxReply.objects.create(inbox_message=message, body="scrap")
        r = api.delete(f"/api/v1/inbox/replies/{reply.id}")
        assert r.status_code == 204
        assert not InboxReply.objects.filter(pk=reply.pk).exists()

    def test_delete_sent_reply_conflicts(self, api, message):
        reply = InboxReply.objects.create(inbox_message=message, body="done", status=InboxReply.Status.SENT)
        r = api.delete(f"/api/v1/inbox/replies/{reply.id}")
        assert r.status_code == 409

    def test_reply_on_foreign_account_message_is_404(self, api, other_account):
        m = _message(other_account, platform_message_id="pm-other")
        reply = InboxReply.objects.create(inbox_message=m, body="x")
        r = api.delete(f"/api/v1/inbox/replies/{reply.id}")
        assert r.status_code == 404


@pytest.mark.django_db
class TestReplyIdempotency:
    @pytest.mark.parametrize("header_key", [False, True])
    @pytest.mark.parametrize("send", [False, True])
    def test_create_replays_without_duplicate_reply_or_send(self, api, message, header_key, send):
        payload = {"body": "thanks", "send": send}
        headers = {"HTTP_IDEMPOTENCY_KEY": "reply-once"} if header_key else {}
        if not header_key:
            payload["idempotency_key"] = "reply-once"
        with patch("apps.inbox.services._dispatch_to_platform", return_value="platform-reply") as dispatch:
            responses = [
                api.post(
                    f"/api/v1/inbox/{message.id}/replies",
                    data=json.dumps(payload),
                    content_type="application/json",
                    **headers,
                )
                for _ in range(2)
            ]
        assert [r.status_code for r in responses] == [201, 201]
        assert responses[0].json() == responses[1].json()
        assert InboxReply.objects.filter(inbox_message=message).count() == 1
        assert dispatch.call_count == int(send)

    @pytest.mark.parametrize("changed_field", ["body", "send", "message"])
    def test_reused_key_with_different_intent_is_rejected(self, api, message, changed_field):
        url = f"/api/v1/inbox/{message.id}/replies"
        payload = {"body": "thanks", "send": False, "idempotency_key": "same-key"}
        first = api.post(url, data=json.dumps(payload), content_type="application/json")
        assert first.status_code == 201
        if changed_field == "message":
            other = _message(message.social_account, platform_message_id="pm-another")
            url = f"/api/v1/inbox/{other.id}/replies"
        else:
            payload[changed_field] = "changed" if changed_field == "body" else True
        with patch("apps.inbox.services._dispatch_to_platform") as dispatch:
            second = api.post(url, data=json.dumps(payload), content_type="application/json")
        assert second.status_code == 422
        assert InboxReply.objects.count() == 1
        dispatch.assert_not_called()

    def test_pending_claim_prevents_creation(self, api, message, full_key):
        from apps.api.middleware import claim_idempotency_slot, fingerprint_request
        from apps.api.schemas import CreateReplyRequest

        url = f"/api/v1/inbox/{message.id}/replies"
        payload = CreateReplyRequest(body="thanks", send=True, idempotency_key="pending")
        claim_idempotency_slot(
            api_key=full_key.api_key,
            idempotency_key="pending",
            fingerprint=fingerprint_request("POST", url, payload.model_dump(mode="json")),
        )
        with patch("apps.inbox.services._dispatch_to_platform") as dispatch:
            response = api.post(url, data=payload.model_dump_json(), content_type="application/json")
        assert response.status_code == 409
        assert InboxReply.objects.count() == 0
        dispatch.assert_not_called()

    def test_validation_failure_releases_header_claim(self, api, message, full_key):
        from apps.api.models import IdempotencyRecord

        url = f"/api/v1/inbox/{message.id}/replies"
        response = api.post(
            url,
            data=json.dumps({"body": "   "}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="retry-validation",
        )
        assert response.status_code == 422
        assert not IdempotencyRecord.objects.filter(api_key=full_key.api_key, key="retry-validation").exists()
        retry = api.post(
            url,
            data=json.dumps({"body": "fixed"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="retry-validation",
        )
        assert retry.status_code == 201

    def test_provider_failure_is_sanitized_and_replayed(self, api, message):
        payload = {"body": "thanks", "send": True, "idempotency_key": "failed-send"}
        with patch(
            "apps.inbox.services._dispatch_to_platform", side_effect=RuntimeError("access_token=private-provider-token")
        ) as dispatch:
            responses = [
                api.post(
                    f"/api/v1/inbox/{message.id}/replies", data=json.dumps(payload), content_type="application/json"
                )
                for _ in range(2)
            ]
        assert [r.status_code for r in responses] == [502, 502]
        assert responses[0].json() == responses[1].json()
        reply = InboxReply.objects.get(inbox_message=message)
        assert reply.status == InboxReply.Status.FAILED
        assert responses[0].json()["detail"] == f"Reply not sent: {reply.send_error}"
        assert "private-provider-token" not in responses[0].content.decode()
        dispatch.assert_called_once()

    def test_body_key_takes_precedence_over_header(self, api, message, full_key):
        from apps.api.models import IdempotencyRecord

        response = api.post(
            f"/api/v1/inbox/{message.id}/replies",
            data=json.dumps({"body": "thanks", "idempotency_key": "body-key"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="header-key",
        )
        assert response.status_code == 201
        assert IdempotencyRecord.objects.filter(api_key=full_key.api_key, key="body-key").exists()
        assert not IdempotencyRecord.objects.filter(api_key=full_key.api_key, key="header-key").exists()

    def test_response_storage_failure_does_not_allow_duplicate_send(self, api, message):
        payload = {"body": "thanks", "send": True, "idempotency_key": "response-failed"}
        url = f"/api/v1/inbox/{message.id}/replies"
        api.raise_request_exception = False
        with patch("apps.inbox.services._dispatch_to_platform", return_value="platform-reply") as dispatch:
            with patch(
                "apps.api.routers.inbox.finalize_idempotent_response", side_effect=RuntimeError("storage failed")
            ):
                first = api.post(url, data=json.dumps(payload), content_type="application/json")
            retry = api.post(url, data=json.dumps(payload), content_type="application/json")
        assert first.status_code == 500
        assert retry.status_code == 409
        assert InboxReply.objects.get(inbox_message=message).status == InboxReply.Status.SENT
        dispatch.assert_called_once()
