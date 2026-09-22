"""HTMX views for drafting, sending and discarding inbox replies."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.inbox.models import InboxMessage, InboxReply
from apps.members.models import WorkspaceMembership
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Draft WS", organization=organization)


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


def _member(workspace, user, role):
    return WorkspaceMembership.objects.create(user=user, workspace=workspace, workspace_role=role)


def _url(workspace, path):
    return f"/workspace/{workspace.id}/inbox/{path}"


@pytest.mark.django_db
def test_save_reply_draft_creates_draft(client, workspace, account, message, org_owner, user):
    _member(workspace, user, WorkspaceMembership.WorkspaceRole.OWNER)
    client.force_login(user)

    resp = client.post(_url(workspace, f"{message.id}/reply/draft/"), {"body": "draft answer"})

    assert resp.status_code == 200
    reply = InboxReply.objects.get(inbox_message=message)
    assert reply.status == InboxReply.Status.DRAFT
    assert reply.body == "draft answer"
    assert reply.author == user
    # The refreshed panel shows the pending draft.
    assert b"draft answer" in resp.content


@pytest.mark.django_db
def test_save_reply_draft_denied_for_viewer(client, workspace, account, message, org_owner, user):
    _member(workspace, user, WorkspaceMembership.WorkspaceRole.VIEWER)
    client.force_login(user)

    resp = client.post(_url(workspace, f"{message.id}/reply/draft/"), {"body": "nope"})

    assert resp.status_code == 403
    assert InboxReply.objects.count() == 0


@pytest.mark.django_db
def test_send_reply_draft_delivers(client, workspace, account, message, org_owner, user):
    _member(workspace, user, WorkspaceMembership.WorkspaceRole.OWNER)
    client.force_login(user)
    reply = InboxReply.objects.create(inbox_message=message, author=user, body="ready")

    with patch("apps.inbox.services._dispatch_to_platform", return_value="plat-9"):
        resp = client.post(_url(workspace, f"replies/{reply.id}/send/"))

    assert resp.status_code == 200
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    assert reply.platform_reply_id == "plat-9"


@pytest.mark.django_db
def test_send_reply_draft_failure_keeps_failed_row(client, workspace, account, message, org_owner, user):
    _member(workspace, user, WorkspaceMembership.WorkspaceRole.OWNER)
    client.force_login(user)
    reply = InboxReply.objects.create(inbox_message=message, author=user, body="ready")

    with patch("apps.inbox.services._dispatch_to_platform", side_effect=RuntimeError("no")):
        resp = client.post(_url(workspace, f"replies/{reply.id}/send/"))

    assert resp.status_code == 200
    assert resp["HX-Reply-Failed"] == "1"
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.FAILED


@pytest.mark.django_db
def test_send_reply_draft_denied_for_viewer(client, workspace, account, message, org_owner, user):
    _member(workspace, user, WorkspaceMembership.WorkspaceRole.VIEWER)
    client.force_login(user)
    reply = InboxReply.objects.create(inbox_message=message, body="ready")

    resp = client.post(_url(workspace, f"replies/{reply.id}/send/"))

    assert resp.status_code == 403
    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.DRAFT


@pytest.mark.django_db
def test_discard_reply_draft_removes_it(client, workspace, account, message, org_owner, user):
    _member(workspace, user, WorkspaceMembership.WorkspaceRole.OWNER)
    client.force_login(user)
    reply = InboxReply.objects.create(inbox_message=message, author=user, body="scrap")

    resp = client.post(_url(workspace, f"replies/{reply.id}/discard/"))

    assert resp.status_code == 200
    assert not InboxReply.objects.filter(pk=reply.pk).exists()


@pytest.mark.django_db
def test_discard_rejects_sent_reply(client, workspace, account, message, org_owner, user):
    _member(workspace, user, WorkspaceMembership.WorkspaceRole.OWNER)
    client.force_login(user)
    reply = InboxReply.objects.create(inbox_message=message, author=user, body="done", status=InboxReply.Status.SENT)

    resp = client.post(_url(workspace, f"replies/{reply.id}/discard/"))

    assert resp.status_code == 409
    assert InboxReply.objects.filter(pk=reply.pk).exists()
