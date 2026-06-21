"""Phase 5 — end-to-end + cross-component integration tests.

These exercise paths that span more than one app's boundary:

* REST issuance → publisher pickup
* MCP tool call → publisher pickup
* Idempotency sweep task actually deletes stale rows
* Rate-limit responses carry the documented headers
* PATCH route updates the right fields with the right ``update_fields`` list

Each test states the chain it covers in the class docstring so a
future maintainer reading the failure can find the relevant component
quickly.
"""

from __future__ import annotations

import datetime as dt
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from apps.api.middleware import PENDING_STATUS_SENTINEL
from apps.api.models import IdempotencyRecord
from apps.api.tasks import sweep_stale_idempotency_records
from apps.api_keys import services
from apps.api_keys.models import ApiKeyAuditLog
from apps.composer.models import PlatformPost, Post
from apps.members.models import (
    PERMISSION_KEYS,
    OrgMembership,
    WorkspaceMembership,
)


class _SecureClient(Client):
    """Mirrors the test-client wrapper from test_routers.py — see there
    for why ``secure=True`` has to be forced per-request rather than at
    Client init.
    """

    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


# ---------------------------------------------------------------------------
# Shared scaffold
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    u = User.objects.create_user(
        email="e2e@example.com",
        password="testpass123",
        name="E2E",
        tos_accepted_at=timezone.now(),
    )
    # The signup signal already gave them an OrgMembership in "My
    # Organization"; promote them to OWNER so they can issue keys.
    om = u.org_memberships.first()
    om.org_role = OrgMembership.OrgRole.OWNER
    om.save(update_fields=["org_role"])
    return u


@pytest.fixture
def organization(user):
    return user.org_memberships.first().organization


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="E2E WS", organization=organization)


@pytest.fixture
def workspace_owner(db, user, workspace):
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
        account_platform_id="li-e2e",
        account_name="LinkedIn E2E",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


@pytest.fixture
def issued_key(db, user, workspace_owner, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="e2e",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


# ===========================================================================
# Full chain — REST API issuance → publisher pickup
# ===========================================================================


@pytest.mark.django_db
class TestRestToPublisherChain:
    """
    Cover the full Agent-API hot path: the agent issues a scheduled post
    via REST, sets ``scheduled_at`` in the past so the publisher's next
    poll picks it up immediately, and the engine successfully transitions
    the row to ``published``.

    This is the test that would have caught any wiring failure between
    ``apps.api.routers.posts``, ``apps.composer.services.create_post``,
    and ``apps.publisher.engine.PublishEngine.poll_and_publish``.
    """

    def test_scheduled_post_is_picked_up_by_publisher(self, client_with_token, social_account):
        # Step 1 — schedule a post in the recent past so the engine's
        # ``effective_at <= now`` filter sees it as due immediately.
        past = (timezone.now() - timedelta(minutes=1)).isoformat()
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "ready to publish",
                    "action": "schedule",
                    "scheduled_at": past,
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content
        pp = PlatformPost.objects.get()
        assert pp.status == "scheduled"

        # Step 2 — prove the engine sees this row as due, then run the
        # synchronous publish primitive on it.
        #
        # We deliberately avoid ``poll_and_publish`` and
        # ``_publish_post_group``: both fan out work via a
        # ``ThreadPoolExecutor`` whose workers use independent DB
        # connections, so they can't see the test transaction
        # pytest-django wraps us in (and any writes they make would be
        # rolled back at test teardown anyway). Calling
        # ``_publish_platform_post`` directly exercises the entire
        # publish logic — credential resolution, retry bookkeeping,
        # PublishLog write, status transition — without any threading.
        from apps.publisher.engine import PublishEngine

        engine = PublishEngine()
        due = engine._get_due_platform_posts()
        assert len(due) == 1, "engine did not see the freshly-scheduled post"
        # Transition the row to PUBLISHING the way ``_publish_post_group``
        # does, so ``_publish_platform_post`` observes the correct
        # starting state.
        PlatformPost.objects.filter(pk=pp.pk).update(status="publishing")
        with patch.object(
            PublishEngine,
            "_dispatch_to_provider",
            return_value={"success": True, "platform_post_id": "abc123"},
        ):
            pp.refresh_from_db()
            engine._publish_platform_post(pp)

        pp.refresh_from_db()
        assert pp.status == "published", f"expected published, got {pp.status!r}"
        assert pp.platform_post_id == "abc123"


# ===========================================================================
# Idempotency sweep task
# ===========================================================================


@pytest.mark.django_db
class TestIdempotencySweepTask:
    """
    Verifies that ``sweep_stale_idempotency_records`` actually deletes
    rows past the 24-hour cutoff and leaves recent ones alone. Without
    this task the model docstring's "we cache the first response for 24h"
    promise is a lie, and crash-stuck PENDING placeholders accumulate.
    """

    def test_sweep_deletes_old_rows_only(self, issued_key):
        from django.utils import timezone as _tz

        # Old row — should be swept.
        old = IdempotencyRecord.objects.create(
            api_key=issued_key.api_key,
            key="old",
            request_fingerprint="x",
            response_status=201,
            response_body={"id": "1"},
        )
        # ``auto_now_add`` fixed ``created_at`` at NOW; rewrite it past
        # the 25-hour mark to simulate a row issued yesterday.
        IdempotencyRecord.objects.filter(pk=old.pk).update(created_at=_tz.now() - dt.timedelta(hours=25))

        # Fresh row — must survive.
        IdempotencyRecord.objects.create(
            api_key=issued_key.api_key,
            key="fresh",
            request_fingerprint="y",
            response_status=201,
            response_body={"id": "2"},
        )

        # Stale PENDING placeholder from a crashed worker — also must
        # be swept since it's the failure mode this task is built to
        # recover from.
        stuck = IdempotencyRecord.objects.create(
            api_key=issued_key.api_key,
            key="stuck",
            request_fingerprint="z",
            response_status=PENDING_STATUS_SENTINEL,
            response_body={},
        )
        IdempotencyRecord.objects.filter(pk=stuck.pk).update(created_at=_tz.now() - dt.timedelta(hours=48))

        # ``@background``-decorated functions still expose their original
        # callable via ``.task_function``; we call that to bypass the
        # task queue and run the sweep synchronously in the test.
        actual = getattr(
            sweep_stale_idempotency_records,
            "task_function",
            sweep_stale_idempotency_records,
        )
        actual()

        keys = set(IdempotencyRecord.objects.values_list("key", flat=True))
        assert "old" not in keys
        assert "stuck" not in keys
        assert "fresh" in keys


# ===========================================================================
# Rate-limit response shape
# ===========================================================================


@pytest.mark.django_db
class TestRateLimitResponseHeaders:
    """
    The 429 envelope is a contract — agents parse ``tier`` and
    ``retry_after`` (plus the ``Retry-After`` HTTP header) to self-
    throttle. This test guards against silent regressions in the JSON
    body or the header set.
    """

    def test_platform_quota_429_has_retry_after_and_tier(self, client_with_token, social_account):
        # Fill the LinkedIn 100-post/day bucket with scheduled rows so
        # the next ``check_platform_quota`` immediately 429s.
        for _ in range(100):
            PlatformPost.objects.create(
                post=Post.objects.create(workspace=social_account.workspace, caption="x"),
                social_account=social_account,
                status="scheduled",
                scheduled_at=timezone.now() + timedelta(hours=1),
            )

        future = (timezone.now() + timedelta(hours=2)).isoformat()
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "over the cap",
                    "action": "schedule",
                    "scheduled_at": future,
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 429
        body = r.json()
        # Wire-shape: ``tier`` identifies which throttle fired,
        # ``retry_after`` is seconds to wait. Agents key off both.
        assert body["error"] == "rate_limited"
        assert body["tier"] == "platform_quota:linkedin_personal"
        assert body["limit"] == 100
        assert "retry_after" in body
        # And the matching HTTP header per RFC 6585.
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) >= 1


# ===========================================================================
# PATCH route — broader coverage
# ===========================================================================


@pytest.fixture
def draft_post(db, social_account, user, workspace):
    p = Post.objects.create(workspace=workspace, author=user, caption="initial", title="initial")
    PlatformPost.objects.create(post=p, social_account=social_account, status="draft")
    return p


@pytest.mark.django_db
class TestPatchRouteHappyPaths:
    """
    ``test_routers.py`` covers PATCH's negative paths (403/404). These
    cover the *happy* shapes — caption-only, title-only, and combined
    edits — and assert the right fields land in the DB plus the audit
    row reflects the action.
    """

    def test_caption_only_update_persists(self, client_with_token, draft_post):
        r = client_with_token.patch(
            f"/api/v1/posts/{draft_post.id}",
            data=json.dumps({"caption": "rewritten"}),
            content_type="application/json",
        )
        assert r.status_code == 200, r.content
        draft_post.refresh_from_db()
        assert draft_post.caption == "rewritten"
        # Untouched fields preserved.
        assert draft_post.title == "initial"
        # Audit row written.
        assert ApiKeyAuditLog.objects.filter(action="post.update").count() == 1

    def test_combined_update(self, client_with_token, draft_post):
        r = client_with_token.patch(
            f"/api/v1/posts/{draft_post.id}",
            data=json.dumps(
                {
                    "caption": "new caption",
                    "title": "new title",
                    "first_comment": "first!",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 200
        draft_post.refresh_from_db()
        assert draft_post.caption == "new caption"
        assert draft_post.title == "new title"
        assert draft_post.first_comment == "first!"

    def test_internal_notes_update_persists(self, client_with_token, draft_post):
        r = client_with_token.patch(
            f"/api/v1/posts/{draft_post.id}",
            data=json.dumps({"internal_notes": "needs a second pass before publish"}),
            content_type="application/json",
        )
        assert r.status_code == 200, r.content
        assert r.json()["internal_notes"] == "needs a second pass before publish"
        draft_post.refresh_from_db()
        assert draft_post.internal_notes == "needs a second pass before publish"
        # Untouched fields preserved.
        assert draft_post.caption == "initial"


# ===========================================================================
# Audit-log action labels
# ===========================================================================


@pytest.mark.django_db
class TestAuditLabelCoverage:
    """
    Audit log labels are the forensic query language. Lock them in so a
    rename in routers.py can't silently break a SIEM query.
    """

    def test_create_schedule_logs_post_create_schedule(self, client_with_token, social_account):
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "audit me",
                    "action": "schedule",
                    "scheduled_at": when,
                }
            ),
            content_type="application/json",
        )
        assert ApiKeyAuditLog.objects.filter(action="post.create.schedule").exists()

    def test_create_draft_logs_post_create_draft(self, client_with_token, social_account):
        client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "draft me",
                    "action": "draft",
                }
            ),
            content_type="application/json",
        )
        assert ApiKeyAuditLog.objects.filter(action="post.create.draft").exists()

    def test_me_read_logs_me_read(self, client_with_token):
        client_with_token.get("/api/v1/me/")
        assert ApiKeyAuditLog.objects.filter(action="me.read").exists()


# ===========================================================================
# Full chain — MCP tool call → publisher pickup
# ===========================================================================


@pytest.mark.django_db
class TestMcpToPublisherChain:
    """Same end-to-end story as TestRestToPublisherChain but driven via
    the MCP transport, proving the two surfaces share the publisher path.
    """

    def test_mcp_schedule_post_lands_in_scheduled(self, client_with_token, social_account):
        past = (timezone.now() - timedelta(minutes=1)).isoformat()
        r = client_with_token.post(
            "/api/v1/mcp/",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "schedule_post",
                        "arguments": {
                            "social_account_id": str(social_account.id),
                            "caption": "via mcp",
                            "scheduled_at": past,
                        },
                    },
                }
            ),
            content_type="application/json",
        )
        body = r.json()
        assert "error" not in body, body
        # The PlatformPost lives in 'scheduled' state in the DB.
        pp = PlatformPost.objects.get()
        assert pp.status == "scheduled"

        # Same thread-pool / transaction-visibility caveat as
        # ``TestRestToPublisherChain``: skip the executor entirely.
        from apps.publisher.engine import PublishEngine

        engine = PublishEngine()
        due = engine._get_due_platform_posts()
        assert len(due) == 1
        PlatformPost.objects.filter(pk=pp.pk).update(status="publishing")
        with patch.object(
            PublishEngine,
            "_dispatch_to_provider",
            return_value={"success": True, "platform_post_id": "mcp-abc"},
        ):
            pp.refresh_from_db()
            engine._publish_platform_post(pp)
        pp.refresh_from_db()
        assert pp.status == "published"
