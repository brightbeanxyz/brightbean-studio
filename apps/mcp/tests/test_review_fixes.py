"""Regression tests for MCP-side review findings.

Covers:
  * #9 — tools/call validates arguments against the published inputSchema
  * #12 — _log_mcp_audit derives status_code from the dispatch envelope,
          not a hardcoded 200
  * #13 — batched JSON-RPC messages each charge against the HTTP rate limit
"""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.api_keys.models import ApiKeyAuditLog
from apps.members.models import (
    PERMISSION_KEYS,
    OrgMembership,
    WorkspaceMembership,
)


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


MCP_URL = "/api/v1/mcp/"


def _rpc(method, params=None, *, id_=1):
    msg = {"jsonrpc": "2.0", "method": method, "id": id_}
    if params is not None:
        msg["params"] = params
    return msg


def _tool_call_msg(name, args, *, id_=1):
    return _rpc("tools/call", {"name": name, "arguments": args}, id_=id_)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="mcpfix@example.com",
        password="testpass123",
        name="MCP Fix",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="MCP Fix Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="WS", organization=organization)


@pytest.fixture
def owner_memberships(db, user, organization, workspace):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
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
        account_platform_id="li-mcpfix",
        account_name="LinkedIn MCP Fix",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="mcpfix",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


# ===========================================================================
# Finding #9 — inputSchema is enforced
# ===========================================================================


@pytest.mark.django_db
class TestInputSchemaEnforcement:
    def test_caption_dict_instead_of_string_returns_invalid_params(self, client_with_token, social_account):
        """Previously this reached the handler with a dict caption that
        Django's TextField stringified to its repr — silent data
        corruption. Now jsonschema validation rejects at the boundary.
        """
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _tool_call_msg(
                    "create_draft",
                    {
                        "social_account_id": str(social_account.id),
                        "caption": {"malicious": "object"},
                    },
                )
            ),
            content_type="application/json",
        )
        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == -32602  # INVALID_PARAMS

    def test_missing_required_field_returns_invalid_params(self, client_with_token):
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _tool_call_msg("create_draft", {})  # no social_account_id, no caption
            ),
            content_type="application/json",
        )
        assert r.json()["error"]["code"] == -32602

    def test_unknown_field_rejected_by_additional_properties_false(self, client_with_token, social_account):
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _tool_call_msg(
                    "create_draft",
                    {
                        "social_account_id": str(social_account.id),
                        "caption": "hi",
                        "rogue_extra_field": True,
                    },
                )
            ),
            content_type="application/json",
        )
        assert r.json()["error"]["code"] == -32602

    def test_well_formed_args_still_succeed(self, client_with_token, social_account):
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _tool_call_msg(
                    "create_draft",
                    {
                        "social_account_id": str(social_account.id),
                        "caption": "valid",
                    },
                )
            ),
            content_type="application/json",
        )
        body = r.json()
        assert "error" not in body, body


# ===========================================================================
# Finding #12 — audit log status derives from JSON-RPC envelope
# ===========================================================================


@pytest.mark.django_db
class TestMcpAuditStatusDerivation:
    def test_invalid_params_logs_4xx_not_200(self, client_with_token, issued_key):
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps(_tool_call_msg("create_draft", {})),
            content_type="application/json",
        )
        # JSON-RPC error envelope inside HTTP 200.
        assert r.status_code == 200
        assert r.json()["error"]["code"] == -32602
        # Audit row reflects the JSON-RPC error.
        latest = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).latest("created_at")
        assert latest.status_code == 422  # INVALID_PARAMS maps to 422

    def test_unknown_method_logs_404(self, client_with_token, issued_key):
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps(_rpc("no/such/method")),
            content_type="application/json",
        )
        assert r.json()["error"]["code"] == -32601
        latest = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).latest("created_at")
        assert latest.status_code == 404  # METHOD_NOT_FOUND maps to 404

    def test_notification_logs_202(self, client_with_token, issued_key):
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),  # no id → notification
            content_type="application/json",
        )
        assert r.status_code == 202
        latest = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).latest("created_at")
        assert latest.status_code == 202


# ===========================================================================
# Finding #13 — batched messages each charge against the rate limit
# ===========================================================================


@pytest.mark.django_db
class TestBatchedRateLimitCharging:
    def test_batch_audits_every_message(self, client_with_token, issued_key):
        """Batch dispatch must audit every message (including notifications)
        and charge the rate limit per message. Notification audit was
        previously dropped in batches; this validates the fix.
        """
        before = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).count()
        r = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                [
                    _rpc("ping", id_=1),
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    _rpc("ping", id_=2),
                ]
            ),
            content_type="application/json",
        )
        assert r.status_code == 200
        after = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).count()
        # 3 messages → 3 audit rows.
        assert after - before == 3
