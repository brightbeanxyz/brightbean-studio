"""OAuth 2.1 authentication for the MCP transport (Claude Desktop connector).

Covers the second credential path ``McpAuth`` adds on top of bb_studio_ keys:
a django-oauth-toolkit access token resolves to a user, maps to their active
workspace, and runs the same tools with that user's permissions. Also asserts
the unauthenticated 401 carries the ``WWW-Authenticate`` challenge that starts
Claude Desktop's OAuth handshake.

The bb_studio_ key path is unchanged and stays covered by ``test_transport``.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.mcp.protocol import INTERNAL_ERROR, INVALID_PARAMS
from apps.members.models import OrgMembership, WorkspaceMembership

MCP_URL = "/api/v1/mcp/"
CLAUDE_REDIRECT = "https://claude.ai/api/mcp/auth_callback"


class _SecureClient(Client):
    """Forces ``secure=True`` so the bearer HTTPS guard doesn't 401 every call."""

    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


def _rpc(method: str, params: dict | None = None, *, id_: int | str | None = 1) -> dict:
    msg: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if id_ is not None:
        msg["id"] = id_
    return msg


def _post(client: Client, body) -> tuple[int, dict | list | None]:
    r = client.post(MCP_URL, data=json.dumps(body), content_type="application/json")
    if r.status_code == 202 or not r.content:
        return r.status_code, None
    return r.status_code, r.json()


def _make_user_with_workspace(email: str, role: str):
    """Create a user + org + workspace + membership + one connected account.

    Sets ``last_workspace_id`` so the OAuth resolver picks this workspace, and
    returns ``(user, workspace, social_account)``.
    """
    from apps.accounts.models import User
    from apps.organizations.models import Organization
    from apps.social_accounts.models import SocialAccount
    from apps.workspaces.models import Workspace

    user = User.objects.create_user(
        email=email,
        password="testpass123",
        name=email,
        tos_accepted_at=timezone.now(),
    )
    org = Organization.objects.create(name=f"Org {email}")
    ws = Workspace.objects.create(name=f"WS {email}", organization=org)
    OrgMembership.objects.create(user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER)
    WorkspaceMembership.objects.create(user=user, workspace=ws, workspace_role=role)
    user.last_workspace_id = ws.id
    user.save(update_fields=["last_workspace_id"])
    sa = SocialAccount.objects.create(
        workspace=ws,
        platform="linkedin_personal",
        account_platform_id=f"li-{email}",
        account_name="LinkedIn OAuth",
        connection_status="connected",
    )
    return user, ws, sa


def _mint_oauth_token(user, *, scope: str = "mcp", expired: bool = False) -> str:
    """Issue a DOT access token for ``user`` and return its raw value.

    ``token_checksum`` (the indexed column our verifier looks up) is populated
    by DOT's own ``save()`` — same path real issued tokens take.
    """
    from oauth2_provider.models import get_access_token_model, get_application_model

    application_model = get_application_model()
    access_token_model = get_access_token_model()
    app = application_model.objects.create(
        name="Claude",
        client_type=application_model.CLIENT_PUBLIC,
        authorization_grant_type=application_model.GRANT_AUTHORIZATION_CODE,
        redirect_uris=CLAUDE_REDIRECT,
    )
    raw = f"oauthtok-{'expired' if expired else 'valid'}-{user.pk}"
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    access_token_model.objects.create(
        user=user,
        application=app,
        token=raw,
        scope=scope,
        expires=timezone.now() + delta,
    )
    return raw


@pytest.mark.django_db
class TestMcpOAuthChallenge:
    def test_unauthenticated_post_advertises_oauth(self):
        c = _SecureClient()
        r = c.post(MCP_URL, data=json.dumps(_rpc("initialize", {})), content_type="application/json")
        assert r.status_code == 401
        challenge = r.headers.get("WWW-Authenticate", "")
        assert challenge.startswith("Bearer ")
        assert "resource_metadata=" in challenge
        assert "/.well-known/oauth-protected-resource/api/v1/mcp" in challenge

    def test_unauthenticated_post_to_no_slash_url_advertises_oauth(self):
        # The metadata's ``resource`` is ``/api/v1/mcp`` and Claude Desktop
        # POSTs there verbatim. Without the no-slash route alias this answered
        # 301 (APPEND_SLASH), the client re-issued the POST as GET, and the
        # OAuth handshake never received its 401 challenge.
        c = _SecureClient()
        r = c.post("/api/v1/mcp", data=json.dumps(_rpc("initialize", {})), content_type="application/json")
        assert r.status_code == 401
        assert "resource_metadata=" in r.headers.get("WWW-Authenticate", "")

    def test_invalid_bearer_returns_401(self):
        c = _SecureClient(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        r = c.post(MCP_URL, data=json.dumps(_rpc("ping")), content_type="application/json")
        assert r.status_code == 401

    def test_expired_token_returns_401(self):
        user, _ws, _sa = _make_user_with_workspace("expired-oauth@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        raw = _mint_oauth_token(user, expired=True)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {raw}")
        r = c.post(MCP_URL, data=json.dumps(_rpc("ping")), content_type="application/json")
        assert r.status_code == 401

    def test_token_for_user_without_workspace_returns_401(self):
        # New users get a default workspace via a post_save signal, so simulate
        # an offboarded user (token still live) by clearing their memberships —
        # this exercises McpAuth's "no usable workspace -> refuse auth" branch.
        from apps.accounts.models import User

        user = User.objects.create_user(
            email="no-ws@example.com",
            password="testpass123",
            name="No WS",
            tos_accepted_at=timezone.now(),
        )
        WorkspaceMembership.objects.filter(user=user).delete()
        raw = _mint_oauth_token(user)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {raw}")
        r = c.post(MCP_URL, data=json.dumps(_rpc("ping")), content_type="application/json")
        assert r.status_code == 401


@pytest.mark.django_db
class TestMcpOAuthSuccess:
    def test_oauth_token_authenticates_ping(self):
        user, _ws, _sa = _make_user_with_workspace("ping-oauth@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        status, body = _post(c, _rpc("ping"))
        assert status == 200
        assert body["result"] == {}

    def test_list_accounts_resolves_active_workspace(self):
        user, _ws, sa = _make_user_with_workspace("owner-oauth@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        status, body = _post(c, _rpc("tools/call", {"name": "list_accounts", "arguments": {}}))
        assert status == 200
        payload = json.loads(body["result"]["content"][0]["text"])
        assert str(sa.id) in {a["id"] for a in payload["accounts"]}

    def test_owner_can_create_draft(self):
        user, _ws, sa = _make_user_with_workspace("creator-oauth@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        status, body = _post(
            c,
            _rpc(
                "tools/call", {"name": "create_draft", "arguments": {"social_account_id": str(sa.id), "caption": "hi"}}
            ),
        )
        assert status == 200
        assert body["result"]["isError"] is False

    def test_viewer_denied_permission_gated_tool(self):
        user, _ws, sa = _make_user_with_workspace("viewer-oauth@example.com", WorkspaceMembership.WorkspaceRole.VIEWER)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        status, body = _post(
            c,
            _rpc(
                "tools/call", {"name": "create_draft", "arguments": {"social_account_id": str(sa.id), "caption": "hi"}}
            ),
        )
        assert body["error"]["code"] == INVALID_PARAMS
        assert "Permission denied" in body["error"]["message"]

    def test_oauth_call_writes_user_attributed_audit_row(self):
        from apps.api_keys.models import ApiKeyAuditLog

        user, _ws, _sa = _make_user_with_workspace("audit-oauth@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        _post(c, _rpc("tools/call", {"name": "list_accounts", "arguments": {}}))
        row = ApiKeyAuditLog.objects.filter(actor_user=user).order_by("-created_at").first()
        assert row is not None
        assert row.api_key_id is None
        assert row.actor_label == "oauth"


@pytest.mark.django_db
class TestOAuthShimCoversToolSurface:
    """Guard against ``OAuthMcpActor`` drift.

    The OAuth shim duck-types the ``ApiKey`` attributes the MCP handlers read
    (``workspace``, ``workspace_id``, ``social_accounts``, ``issued_by`` /
    ``issued_by_id``). If a handler ever reads an attribute the shim doesn't
    provide, it surfaces as a JSON-RPC ``INTERNAL_ERROR`` (the dispatcher wraps
    the ``AttributeError``), not a clean ``INVALID_PARAMS`` — so these tests
    turn that latent runtime break into a CI failure.
    """

    def test_no_registered_tool_internal_errors_via_oauth(self):
        # Drive every registered tool once over the OAuth path. Tools with
        # required args fail schema validation (INVALID_PARAMS) before their
        # body runs; no tool should ever hit INTERNAL_ERROR, which would mean
        # the shim is missing an attribute the handler touched.
        from apps.mcp.tools import all_tools

        user, _ws, _sa = _make_user_with_workspace("surface-oauth@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")

        tool_names = [t.name for t in all_tools()]
        assert tool_names, "expected MCP tools to be registered"

        internal_errors = []
        for name in tool_names:
            status, body = _post(c, _rpc("tools/call", {"name": name, "arguments": {}}))
            assert status == 200, f"{name}: unexpected HTTP {status}"
            err = body.get("error") if isinstance(body, dict) else None
            if err and err.get("code") == INTERNAL_ERROR:
                internal_errors.append((name, err.get("message")))

        assert not internal_errors, f"OAuthMcpActor shim is missing attributes these tools need: {internal_errors}"

    def test_get_post_reaches_workspace_scoped_query(self):
        # get_post with a valid-but-nonexistent UUID drives _get_post_for_key,
        # which reads api_key.workspace_id off the shim — the one attribute the
        # broad loop above and the create_draft test don't exercise. Reaching
        # "Post not found" (INVALID_PARAMS) proves the workspace-scoped query ran.
        user, _ws, _sa = _make_user_with_workspace("getpost-oauth@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        status, body = _post(
            c,
            _rpc("tools/call", {"name": "get_post", "arguments": {"post_id": "00000000-0000-0000-0000-000000000000"}}),
        )
        assert status == 200
        assert body["error"]["code"] == INVALID_PARAMS
        assert "not found" in body["error"]["message"].lower()


@pytest.mark.django_db
class TestOAuthInternalNotesVisibility:
    """``internal_notes`` is team-only. ``get_post`` isn't permission-gated, so
    the shared ``PostResponse`` serializer must redact the field for
    client/viewer-role OAuth callers (whom the composer also blocks from seeing
    internal notes) while internal roles keep seeing it.
    """

    def _post_with_note(self, ws, user, sa, note="board-only context"):
        from apps.composer.models import PlatformPost, Post

        post = Post.objects.create(workspace=ws, author=user, caption="public", internal_notes=note)
        PlatformPost.objects.create(post=post, social_account=sa, status="draft")
        return post

    def test_viewer_get_post_redacts_internal_notes(self):
        user, ws, sa = _make_user_with_workspace("viewer-notes@example.com", WorkspaceMembership.WorkspaceRole.VIEWER)
        post = self._post_with_note(ws, user, sa)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        status, body = _post(c, _rpc("tools/call", {"name": "get_post", "arguments": {"post_id": str(post.id)}}))
        assert status == 200
        payload = json.loads(body["result"]["content"][0]["text"])
        assert payload["internal_notes"] == ""  # redacted for a viewer
        assert payload["caption"] == "public"  # other fields intact

    def test_owner_get_post_includes_internal_notes(self):
        user, ws, sa = _make_user_with_workspace("owner-notes@example.com", WorkspaceMembership.WorkspaceRole.OWNER)
        post = self._post_with_note(ws, user, sa)
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")
        status, body = _post(c, _rpc("tools/call", {"name": "get_post", "arguments": {"post_id": str(post.id)}}))
        assert status == 200
        payload = json.loads(body["result"]["content"][0]["text"])
        assert payload["internal_notes"] == "board-only context"
