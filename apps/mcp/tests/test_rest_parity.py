"""Gap 4 + 5 regression: MCP and REST must serialize Post identically.

Both surfaces delegate to ``apps.api.schemas.PostResponse.from_post`` so
they cannot drift in either field set (Gap 4: previously the MCP body
omitted ``created_at``, ``updated_at``, and ``platform_post_id``) or
wire format (Gap 5: previously REST emitted ``2026-06-15T09:00:00Z``
while MCP emitted ``2026-06-15T09:00:00+00:00``).

If these fail, do NOT hand-fix the MCP serializer — fix
``PostResponse.from_post`` and the failure goes away in both places.
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
    return {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": id_}


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="parity@example.com",
        password="testpass123",
        name="Parity",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Parity Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Parity Workspace", organization=organization)


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
        account_platform_id="li-parity",
        account_name="Parity LinkedIn",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="parity",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


@pytest.fixture
def scheduled_post(db, user, workspace, social_account):
    """A scheduled Post with one PlatformPost child plus a non-empty
    ``platform_post_id`` so we exercise every field the old MCP serializer
    used to drop. ``Post.status`` is a property derived from children, so
    we set the status on the PlatformPost only.
    """
    when = timezone.now() + timedelta(hours=2)
    post = Post.objects.create(
        workspace=workspace,
        author=user,
        title="Parity title",
        caption="Parity caption",
        first_comment="Parity first comment",
        internal_notes="Parity internal note",
        scheduled_at=when,
    )
    PlatformPost.objects.create(
        post=post,
        social_account=social_account,
        status="scheduled",
        scheduled_at=when,
        platform_post_id="upstream-abc-123",
    )
    return post


@pytest.mark.django_db
class TestRestMcpPostParity:
    def test_mcp_get_post_and_rest_get_post_return_identical_bodies(self, client_with_token, scheduled_post):
        rest = client_with_token.get(f"/api/v1/posts/{scheduled_post.id}")
        assert rest.status_code == 200, rest.content
        rest_body = rest.json()

        mcp = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {"name": "get_post", "arguments": {"post_id": str(scheduled_post.id)}},
                )
            ),
            content_type="application/json",
        )
        assert mcp.status_code == 200
        mcp_envelope = mcp.json()
        assert "error" not in mcp_envelope, mcp_envelope
        mcp_body = json.loads(mcp_envelope["result"]["content"][0]["text"])

        assert mcp_body == rest_body, (
            "MCP and REST disagree on the Post payload. "
            "Likely _serialize_post in apps/mcp/handlers.py drifted from "
            "PostResponse.from_post — they MUST share the schema."
        )

    def test_mcp_payload_includes_gap_4_fields(self, client_with_token, scheduled_post):
        """Gap 4: ``created_at``, ``updated_at``, ``platform_post_id`` were
        previously absent on the MCP side.
        """
        mcp = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {"name": "get_post", "arguments": {"post_id": str(scheduled_post.id)}},
                )
            ),
            content_type="application/json",
        )
        body = json.loads(mcp.json()["result"]["content"][0]["text"])
        assert "created_at" in body
        assert "updated_at" in body
        assert body["platform_posts"][0]["platform_post_id"] == "upstream-abc-123"

    def test_internal_notes_round_trips_through_mcp_create_draft(self, client_with_token, social_account):
        """internal_notes set via MCP ``create_draft`` must come back on the MCP
        response *and* match what REST returns for the same post — proving the
        field threads through the shared ``create_post`` service and
        ``PostResponse`` rather than a surface-specific code path.
        """
        note = "Cleared with the client on the 2pm call."
        mcp = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {
                        "name": "create_draft",
                        "arguments": {
                            "social_account_id": str(social_account.id),
                            "caption": "draft with a note",
                            "internal_notes": note,
                        },
                    },
                )
            ),
            content_type="application/json",
        )
        assert mcp.status_code == 200
        envelope = mcp.json()
        assert "error" not in envelope, envelope
        mcp_body = json.loads(envelope["result"]["content"][0]["text"])
        assert mcp_body["internal_notes"] == note

        rest = client_with_token.get(f"/api/v1/posts/{mcp_body['id']}")
        assert rest.status_code == 200, rest.content
        assert rest.json()["internal_notes"] == note

    def test_mcp_scheduled_at_uses_z_suffix_for_utc(self, client_with_token, scheduled_post):
        """Gap 5: MCP used to emit ``+00:00``; both surfaces now emit ``Z``."""
        mcp = client_with_token.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {"name": "get_post", "arguments": {"post_id": str(scheduled_post.id)}},
                )
            ),
            content_type="application/json",
        )
        body = json.loads(mcp.json()["result"]["content"][0]["text"])
        assert body["scheduled_at"].endswith("Z"), body["scheduled_at"]
        assert "+00:00" not in body["scheduled_at"]
        assert body["platform_posts"][0]["scheduled_at"].endswith("Z")


# ---------------------------------------------------------------------------
# Analytics parity — same builder powers REST + MCP, so payloads must match.
# ---------------------------------------------------------------------------


@pytest.fixture
def instagram_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-parity",
        account_name="Parity IG",
        follower_count=500,
        connection_status="connected",
    )


@pytest.fixture
def analytics_key(db, user, owner_memberships, workspace, instagram_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[instagram_account],
        issued_by=user,
        name="analytics-parity",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def analytics_client(analytics_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {analytics_key.plaintext_token}")


@pytest.fixture
def published_ig_post(db, workspace, instagram_account):
    """Published IG post with both account- and post-level snapshots."""
    from apps.analytics.metrics import PLATFORM_METRICS, post_metrics_for
    from apps.analytics.models import (
        AccountInsightsSnapshot,
        PostInsightsSnapshot,
    )

    published_at = timezone.now() - timedelta(hours=12)
    post = Post.objects.create(workspace=workspace, caption="parity post")
    pp = PlatformPost.objects.create(
        post=post,
        social_account=instagram_account,
        status="published",
        published_at=published_at,
        platform_post_id="ig-parity-xyz",
    )

    end = timezone.now().date()
    for metric in PLATFORM_METRICS["instagram"]:
        for offset in range(14):
            AccountInsightsSnapshot.objects.create(
                social_account=instagram_account,
                metric_key=metric,
                date=end - timedelta(days=13 - offset),
                value=20.0 + offset,
            )
    for metric in post_metrics_for("instagram"):
        for offset in range(2):
            PostInsightsSnapshot.objects.create(
                platform_post=pp,
                metric_key=metric,
                date=end - timedelta(days=1 - offset),
                value=3.0 + offset,
            )
    return post, pp


@pytest.mark.django_db
class TestRestMcpAnalyticsParity:
    def test_account_analytics_bodies_match(self, analytics_client, instagram_account, published_ig_post):
        rest = analytics_client.get(f"/api/v1/analytics/accounts/{instagram_account.id}?days=7")
        assert rest.status_code == 200, rest.content
        rest_body = rest.json()

        mcp = analytics_client.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {
                        "name": "get_account_analytics",
                        "arguments": {"account_id": str(instagram_account.id), "days": 7},
                    },
                )
            ),
            content_type="application/json",
        )
        assert mcp.status_code == 200
        envelope = mcp.json()
        assert "error" not in envelope, envelope
        mcp_body = json.loads(envelope["result"]["content"][0]["text"])

        assert mcp_body == rest_body, (
            "MCP and REST disagree on the AccountAnalyticsResponse payload. "
            "Both surfaces must call build_account_analytics — do not hand-shape one side."
        )

    def test_post_analytics_bodies_match(self, analytics_client, published_ig_post):
        post, _pp = published_ig_post
        rest = analytics_client.get(f"/api/v1/analytics/posts/{post.id}")
        assert rest.status_code == 200, rest.content
        rest_body = rest.json()

        mcp = analytics_client.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {"name": "get_post_analytics", "arguments": {"post_id": str(post.id)}},
                )
            ),
            content_type="application/json",
        )
        assert mcp.status_code == 200
        envelope = mcp.json()
        assert "error" not in envelope, envelope
        mcp_body = json.loads(envelope["result"]["content"][0]["text"])

        assert mcp_body == rest_body, (
            "MCP and REST disagree on the PostAnalyticsResponse payload. "
            "Both surfaces must call build_post_analytics — do not hand-shape one side."
        )


# ---------------------------------------------------------------------------
# Analytics permission gate — the MCP analytics tools require view_analytics,
# same as the REST routes.
# ---------------------------------------------------------------------------


@pytest.fixture
def analytics_key_no_perm(db, user, owner_memberships, workspace, instagram_account):
    """Key allowlisted on the IG account but lacking ``view_analytics``."""
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[instagram_account],
        issued_by=user,
        name="analytics-noperm",
        permissions=[p for p in PERMISSION_KEYS if p != "view_analytics"],
    )


@pytest.fixture
def analytics_client_no_perm(analytics_key_no_perm):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {analytics_key_no_perm.plaintext_token}")


@pytest.mark.django_db
class TestMcpAnalyticsPermissionGate:
    def test_account_analytics_tool_requires_view_analytics(self, analytics_client_no_perm, instagram_account):
        mcp = analytics_client_no_perm.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {"name": "get_account_analytics", "arguments": {"account_id": str(instagram_account.id)}},
                )
            ),
            content_type="application/json",
        )
        body = mcp.json()
        assert "error" in body, body
        assert "permission denied" in body["error"]["message"].lower()

    def test_post_analytics_tool_requires_view_analytics(self, analytics_client_no_perm, published_ig_post):
        post, _pp = published_ig_post
        mcp = analytics_client_no_perm.post(
            MCP_URL,
            data=json.dumps(
                _rpc(
                    "tools/call",
                    {"name": "get_post_analytics", "arguments": {"post_id": str(post.id)}},
                )
            ),
            content_type="application/json",
        )
        body = mcp.json()
        assert "error" in body, body
        assert "permission denied" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# proposed_publish_at — create_draft carries it; every post payload returns it.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProposedPublishAtMcp:
    _WHEN = "2027-09-01T09:00:00Z"

    def _call(self, client, name, arguments):
        resp = client.post(
            MCP_URL,
            data=json.dumps(_rpc("tools/call", {"name": name, "arguments": arguments})),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        envelope = resp.json()
        assert "error" not in envelope, envelope
        return json.loads(envelope["result"]["content"][0]["text"])

    def test_create_draft_with_proposed_round_trips_through_get_post(self, client_with_token, social_account):
        created = self._call(
            client_with_token,
            "create_draft",
            {
                "social_account_id": str(social_account.id),
                "caption": "hi",
                "proposed_publish_at": self._WHEN,
            },
        )
        assert created["proposed_publish_at"] == self._WHEN
        fetched = self._call(client_with_token, "get_post", {"post_id": created["id"]})
        assert fetched["proposed_publish_at"] == self._WHEN

    def test_create_draft_without_proposed_is_null(self, client_with_token, social_account):
        created = self._call(
            client_with_token,
            "create_draft",
            {"social_account_id": str(social_account.id), "caption": "hi"},
        )
        assert created["proposed_publish_at"] is None

    def test_schedule_draft_clears_proposed(self, client_with_token, social_account):
        created = self._call(
            client_with_token,
            "create_draft",
            {"social_account_id": str(social_account.id), "caption": "hi", "proposed_publish_at": self._WHEN},
        )
        assert created["proposed_publish_at"] == self._WHEN
        when = (timezone.now() + timedelta(hours=3)).isoformat().replace("+00:00", "Z")
        scheduled = self._call(client_with_token, "schedule_draft", {"post_id": created["id"], "scheduled_at": when})
        assert scheduled["scheduled_at"] is not None
        assert scheduled["proposed_publish_at"] is None
        fetched = self._call(client_with_token, "get_post", {"post_id": created["id"]})
        assert fetched["proposed_publish_at"] is None

    def test_create_draft_naive_proposed_stored_as_utc(self, client_with_token, social_account):
        created = self._call(
            client_with_token,
            "create_draft",
            {
                "social_account_id": str(social_account.id),
                "caption": "hi",
                "proposed_publish_at": "2027-09-01T09:00:00",
            },
        )
        # A tz-less value is interpreted as UTC and serialized with a Z suffix.
        assert created["proposed_publish_at"] == "2027-09-01T09:00:00Z"
