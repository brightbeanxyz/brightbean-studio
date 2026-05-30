"""Phase 3 — MCP Streamable HTTP transport end-to-end.

Exercises the protocol layer (initialize, ping, tools/list, tools/call,
notifications, batches, JSON-RPC errors), the auth integration (same
bearer token as REST), and the tool handlers' security gates
(allowlist enforcement, permission re-checks).
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.composer.models import PlatformPost, Post
from apps.members.models import (
    OrgMembership,
    PERMISSION_KEYS,
    WorkspaceMembership,
)
from apps.mcp.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)


# ---------------------------------------------------------------------------
# Test client — forces ``secure=True`` so ApiKeyAuth's HTTPS guard
# doesn't reject every request with 400. Same pattern as the REST tests.
# ---------------------------------------------------------------------------


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


MCP_URL = "/api/v1/mcp/"


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


# ---------------------------------------------------------------------------
# Fixtures — minimal scaffold mirroring the REST test setup.
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="mcp-owner@example.com",
        password="testpass123",
        name="MCP Owner",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="MCP Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="MCP Workspace", organization=organization)


@pytest.fixture
def owner_memberships(db, user, organization, workspace):
    OrgMembership.objects.create(
        user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER
    )
    return WorkspaceMembership.objects.create(
        user=user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )


@pytest.fixture
def social_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-mcp",
        account_name="LinkedIn MCP",
        connection_status="connected",
    )


@pytest.fixture
def second_account(db, workspace):
    """A SocialAccount in the same workspace that the MCP key is NOT
    scoped to — used for confused-deputy regression tests.
    """
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-mcp-second",
        account_name="LinkedIn MCP 2",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="mcp",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMcpAuth:
    def test_missing_bearer_returns_401(self):
        c = _SecureClient()
        r = c.post(MCP_URL, data=json.dumps(_rpc("ping")), content_type="application/json")
        assert r.status_code == 401

    def test_valid_bearer_passes(self, client_with_token):
        status, body = _post(client_with_token, _rpc("ping"))
        assert status == 200
        assert body["jsonrpc"] == "2.0"
        assert body["result"] == {}


# ---------------------------------------------------------------------------
# Protocol mechanics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProtocolMechanics:
    def test_initialize_returns_server_info(self, client_with_token):
        status, body = _post(
            client_with_token,
            _rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}}),
        )
        assert status == 200
        result = body["result"]
        assert result["serverInfo"]["name"] == "brightbean-studio"
        assert "protocolVersion" in result
        assert "tools" in result["capabilities"]

    def test_notification_returns_202_no_body(self, client_with_token):
        """Notifications have no ``id`` and per JSON-RPC must not get a reply."""
        msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        r = client_with_token.post(
            MCP_URL, data=json.dumps(msg), content_type="application/json"
        )
        assert r.status_code == 202
        assert r.content == b""

    def test_unknown_method_returns_method_not_found(self, client_with_token):
        status, body = _post(client_with_token, _rpc("does/not/exist"))
        assert status == 200  # JSON-RPC errors travel inside a 200
        assert body["error"]["code"] == METHOD_NOT_FOUND

    def test_invalid_json_returns_parse_error(self, client_with_token):
        r = client_with_token.post(
            MCP_URL, data="{not json", content_type="application/json"
        )
        assert r.status_code == 400
        body = r.json()
        assert body["error"]["code"] == PARSE_ERROR

    def test_batch_of_two_returns_array_of_two(self, client_with_token):
        status, body = _post(
            client_with_token,
            [_rpc("ping", id_=1), _rpc("ping", id_=2)],
        )
        assert status == 200
        assert isinstance(body, list)
        assert {b["id"] for b in body} == {1, 2}

    def test_empty_batch_is_400(self, client_with_token):
        r = client_with_token.post(
            MCP_URL, data="[]", content_type="application/json"
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tools — list + dispatch
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestToolsList:
    def test_tools_list_returns_registered_tools(self, client_with_token):
        status, body = _post(client_with_token, _rpc("tools/list"))
        assert status == 200
        names = {t["name"] for t in body["result"]["tools"]}
        assert {"list_accounts", "create_draft", "schedule_post", "get_post", "cancel_post"} <= names

    def test_each_tool_has_an_input_schema(self, client_with_token):
        status, body = _post(client_with_token, _rpc("tools/list"))
        for t in body["result"]["tools"]:
            assert t["inputSchema"]["type"] == "object"

    def test_unknown_tool_call_returns_invalid_params(self, client_with_token):
        status, body = _post(
            client_with_token,
            _rpc("tools/call", {"name": "no_such_tool", "arguments": {}}),
        )
        assert body["error"]["code"] == INVALID_PARAMS


# ---------------------------------------------------------------------------
# Tool: list_accounts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListAccountsTool:
    def test_returns_only_allowlisted_accounts(
        self, client_with_token, social_account, second_account
    ):
        status, body = _post(
            client_with_token,
            _rpc("tools/call", {"name": "list_accounts", "arguments": {}}),
        )
        # Tool returns wrapped text content with JSON inside.
        result = body["result"]
        assert result["isError"] is False
        inner = json.loads(result["content"][0]["text"])
        ids = {a["id"] for a in inner["accounts"]}
        assert ids == {str(social_account.id)}
        # second_account exists in the same workspace but is NOT in the
        # key's allowlist — must not appear here.
        assert str(second_account.id) not in ids


# ---------------------------------------------------------------------------
# Tool: create_draft
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateDraftTool:
    def test_creates_a_draft(self, client_with_token, social_account):
        status, body = _post(
            client_with_token,
            _rpc(
                "tools/call",
                {
                    "name": "create_draft",
                    "arguments": {
                        "social_account_id": str(social_account.id),
                        "caption": "hello mcp",
                    },
                },
            ),
        )
        assert status == 200
        assert "error" not in body
        inner = json.loads(body["result"]["content"][0]["text"])
        assert inner["caption"] == "hello mcp"
        assert inner["platform_posts"][0]["status"] == "draft"
        # And the row really exists in the DB.
        assert Post.objects.count() == 1
        assert PlatformPost.objects.filter(status="draft").count() == 1

    def test_rejects_account_outside_allowlist(
        self, client_with_token, second_account
    ):
        status, body = _post(
            client_with_token,
            _rpc(
                "tools/call",
                {
                    "name": "create_draft",
                    "arguments": {
                        "social_account_id": str(second_account.id),
                        "caption": "should not be allowed",
                    },
                },
            ),
        )
        assert body["error"]["code"] == INVALID_PARAMS
        assert "allowlist" in body["error"]["message"].lower()
        assert Post.objects.count() == 0

    def test_missing_required_arguments_returns_invalid_params(
        self, client_with_token
    ):
        status, body = _post(
            client_with_token,
            _rpc("tools/call", {"name": "create_draft", "arguments": {}}),
        )
        assert body["error"]["code"] == INVALID_PARAMS


# ---------------------------------------------------------------------------
# Tool: schedule_post
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSchedulePostTool:
    def test_creates_a_scheduled_post(self, client_with_token, social_account):
        when = (timezone.now() + timedelta(hours=2)).isoformat()
        status, body = _post(
            client_with_token,
            _rpc(
                "tools/call",
                {
                    "name": "schedule_post",
                    "arguments": {
                        "social_account_id": str(social_account.id),
                        "caption": "scheduled via mcp",
                        "scheduled_at": when,
                    },
                },
            ),
        )
        assert "error" not in body, body
        inner = json.loads(body["result"]["content"][0]["text"])
        assert inner["platform_posts"][0]["status"] == "scheduled"


# ---------------------------------------------------------------------------
# Tool: get_post + allowlist enforcement
# ---------------------------------------------------------------------------


@pytest.fixture
def own_post(db, social_account, user, workspace):
    """A Post fully within the key's allowlist — get_post should succeed."""
    p = Post.objects.create(workspace=workspace, author=user, caption="mine")
    PlatformPost.objects.create(post=p, social_account=social_account, status="draft")
    return p


@pytest.fixture
def foreign_post(db, second_account, user, workspace):
    """A Post whose only child targets ``second_account`` — outside the
    key's allowlist. get_post must report 'Post not found'.
    """
    p = Post.objects.create(workspace=workspace, author=user, caption="not mine")
    PlatformPost.objects.create(post=p, social_account=second_account, status="draft")
    return p


@pytest.mark.django_db
class TestGetPostTool:
    def test_get_own_post_succeeds(self, client_with_token, own_post):
        status, body = _post(
            client_with_token,
            _rpc(
                "tools/call",
                {"name": "get_post", "arguments": {"post_id": str(own_post.id)}},
            ),
        )
        assert "error" not in body
        inner = json.loads(body["result"]["content"][0]["text"])
        assert inner["id"] == str(own_post.id)

    def test_get_foreign_post_is_not_found(self, client_with_token, foreign_post):
        """Regression for the allowlist enforcement Codex flagged in REST:
        MCP must NOT leak posts whose children are outside scope, even via
        a tool call that knows the UUID.
        """
        status, body = _post(
            client_with_token,
            _rpc(
                "tools/call",
                {"name": "get_post", "arguments": {"post_id": str(foreign_post.id)}},
            ),
        )
        assert body["error"]["code"] == INVALID_PARAMS
        assert "not found" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Tool: cancel_post
# ---------------------------------------------------------------------------


@pytest.fixture
def scheduled_post(db, social_account, user, workspace):
    p = Post.objects.create(workspace=workspace, author=user, caption="will cancel")
    PlatformPost.objects.create(
        post=p,
        social_account=social_account,
        status="scheduled",
        scheduled_at=timezone.now() + timedelta(hours=1),
    )
    return p


@pytest.mark.django_db
class TestCancelPostTool:
    def test_cancel_transitions_scheduled_to_draft(
        self, client_with_token, scheduled_post
    ):
        status, body = _post(
            client_with_token,
            _rpc(
                "tools/call",
                {"name": "cancel_post", "arguments": {"post_id": str(scheduled_post.id)}},
            ),
        )
        assert "error" not in body, body
        inner = json.loads(body["result"]["content"][0]["text"])
        assert inner["platform_posts"][0]["status"] == "draft"


# ---------------------------------------------------------------------------
# Permission gating — keys lacking ``create_posts`` cannot mutate
# ---------------------------------------------------------------------------


@pytest.fixture
def read_only_membership(db, organization, workspace):
    """A user with a workspace VIEWER role (no create_posts permission)
    but with org-level ``manage_api_keys`` so they CAN issue keys.
    Used to exercise the per-request permission intersection on MCP tools.
    """
    from apps.accounts.models import User

    u = User.objects.create_user(
        email="ro@example.com",
        password="testpass123",
        name="RO",
        tos_accepted_at=timezone.now(),
    )
    OrgMembership.objects.create(
        user=u, organization=organization, org_role=OrgMembership.OrgRole.ADMIN
    )
    return WorkspaceMembership.objects.create(
        user=u,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.VIEWER,
    )


@pytest.fixture
def read_only_key(db, read_only_membership, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=read_only_membership.user,
        name="ro",
        # Empty — the viewer doesn't hold create_posts, so the issuance
        # intersection check forces an empty permission set.
        permissions=[],
    )


@pytest.fixture
def read_only_client(read_only_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {read_only_key.plaintext_token}")


@pytest.mark.django_db
class TestPermissionGating:
    def test_read_only_key_cannot_create_draft(
        self, read_only_client, social_account
    ):
        status, body = _post(
            read_only_client,
            _rpc(
                "tools/call",
                {
                    "name": "create_draft",
                    "arguments": {
                        "social_account_id": str(social_account.id),
                        "caption": "denied",
                    },
                },
            ),
        )
        assert body["error"]["code"] == INVALID_PARAMS
        assert "permission denied" in body["error"]["message"].lower()

    def test_read_only_key_can_still_list_accounts(
        self, read_only_client, social_account
    ):
        """list_accounts has no permission requirement — it's pure scope echo.
        A read-only key must be able to call it.
        """
        status, body = _post(
            read_only_client,
            _rpc("tools/call", {"name": "list_accounts", "arguments": {}}),
        )
        assert "error" not in body, body
