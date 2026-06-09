"""Round-2 review-fix regression tests.

Each test maps to one finding from the second Codex pass — see the
class docstring for the link.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.api.limits import (
    PLATFORM_DAILY_POST_LIMIT,
    count_recent_creations,
    resolve_platform_limit,
)
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


# ---------------------------------------------------------------------------
# Shared scaffold
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    u = User.objects.create_user(
        email="r2@example.com",
        password="testpass123",
        name="R2",
        tos_accepted_at=timezone.now(),
    )
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

    return Workspace.objects.create(name="R2 WS", organization=organization)


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
        account_platform_id="li-r2",
        account_name="LinkedIn R2",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


# ===========================================================================
# P1 — Scheduling requires publish_directly
# ===========================================================================


@pytest.fixture
def write_only_membership(db, organization, workspace):
    """An EDITOR — holds ``create_posts`` but NOT ``publish_directly``.
    This is the key class Codex flagged: it could create scheduled
    posts via the API before this fix, bypassing the composer's
    publish-direct gate.
    """
    from apps.accounts.models import User

    u = User.objects.create_user(
        email="r2-editor@example.com",
        password="testpass123",
        name="R2 Editor",
        tos_accepted_at=timezone.now(),
    )
    OrgMembership.objects.create(user=u, organization=organization, org_role=OrgMembership.OrgRole.ADMIN)
    return WorkspaceMembership.objects.create(
        user=u,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.EDITOR,
    )


@pytest.fixture
def write_only_key(write_only_membership, workspace, social_account):
    """A key issued by the editor with only ``create_posts``."""
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=write_only_membership.user,
        name="ro-schedule",
        permissions=["create_posts"],
    )


@pytest.fixture
def write_only_client(write_only_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {write_only_key.plaintext_token}")


@pytest.mark.django_db
class TestScheduleRequiresPublishDirectly:
    def test_create_action_schedule_rejected_without_publish_directly(self, write_only_client, social_account):
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = write_only_client.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "should be 403",
                    "action": "schedule",
                    "scheduled_at": when,
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 403
        assert "publish_directly" in r.json()["detail"]
        # And nothing was created.
        assert Post.objects.count() == 0

    def test_create_action_draft_still_allowed_without_publish_directly(self, write_only_client, social_account):
        """The gate must only fire on schedule — draft creation is the
        whole point of a ``create_posts``-only key.
        """
        r = write_only_client.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "draft is fine",
                    "action": "draft",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201

    def test_schedule_route_rejected_without_publish_directly(
        self, write_only_client, write_only_membership, workspace, social_account
    ):
        # Pre-create a draft via the service (bypasses HTTP perm checks
        # so we can isolate the schedule route's check).
        post = Post.objects.create(workspace=workspace, caption="x")
        PlatformPost.objects.create(post=post, social_account=social_account, status="draft")
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = write_only_client.post(
            f"/api/v1/posts/{post.id}/schedule",
            data=json.dumps({"scheduled_at": when}),
            content_type="application/json",
        )
        assert r.status_code == 403


# ===========================================================================
# Codex PR #53 follow-up — POST /posts/{id}/schedule honours approval workflow
# ===========================================================================


@pytest.mark.django_db
class TestScheduleRouteHonoursApprovalWorkflow:
    """Regression test for the Codex PR #53 P1: ``create_post(status=
    "scheduled")`` rejects direct scheduling when the workspace requires
    approval, but the standalone ``POST /posts/{id}/schedule`` route
    used to bypass that check — so an agent could create a draft and
    then promote it via that route without routing through the
    approval workflow. The gate now lives in ``transition_platform_post``
    so every draft → scheduled path is covered.
    """

    def test_schedule_route_blocked_when_workspace_requires_approval(
        self, user, workspace_owner, workspace, social_account
    ):
        from apps.api_keys import services

        workspace.approval_workflow_mode = "required_internal"
        workspace.save(update_fields=["approval_workflow_mode"])

        # Issue a key with both create_posts AND publish_directly so the
        # route-level permission gates pass — the approval-mode check is
        # the only thing that should reject.
        key = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=user,
            name="approval-gate",
            permissions=["create_posts", "publish_directly"],
        )
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {key.plaintext_token}")

        # Pre-create a draft directly (bypassing create_post so we can
        # isolate the schedule route).
        post = Post.objects.create(workspace=workspace, caption="needs approval")
        PlatformPost.objects.create(post=post, social_account=social_account, status="draft")

        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = c.post(
            f"/api/v1/posts/{post.id}/schedule",
            data=json.dumps({"scheduled_at": when}),
            content_type="application/json",
        )
        assert r.status_code == 422
        assert "approval" in r.json()["detail"].lower()
        # And the draft is unchanged.
        pp = PlatformPost.objects.get(post=post)
        assert pp.status == "draft"


# ===========================================================================
# P2 — Cancelling the last scheduled child clears Post.scheduled_at
# ===========================================================================


@pytest.fixture
def owner_key(db, user, workspace_owner, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="r2-owner",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def owner_client(owner_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {owner_key.plaintext_token}")


@pytest.mark.django_db
class TestCancelClearsParentSchedule:
    def test_canceling_last_scheduled_child_clears_post_scheduled_at(
        self, owner_client, social_account, workspace, user
    ):
        """Codex P2 regression: ``sync_post_scheduled_at`` previously
        returned early when no child had ``scheduled_at``, so the Post
        kept its stale ``scheduled_at`` value after cancellation —
        calendars and dashboards then showed a draft as scheduled.
        """
        post = Post.objects.create(
            workspace=workspace,
            author=user,
            caption="cancel me",
            scheduled_at=timezone.now() + timedelta(hours=1),
        )
        PlatformPost.objects.create(
            post=post,
            social_account=social_account,
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(hours=1),
        )

        r = owner_client.post(f"/api/v1/posts/{post.id}/cancel")
        assert r.status_code == 200, r.content
        post.refresh_from_db()
        assert post.scheduled_at is None, (
            "parent scheduled_at must be cleared when the last scheduled "
            "child is cancelled; otherwise listings keep showing the post "
            "as scheduled"
        )


# ===========================================================================
# P3 — Quota counts via updated_at, not created_at
# ===========================================================================


@pytest.mark.django_db
class TestQuotaCountsRecentTransitions:
    def test_old_draft_freshly_scheduled_counts_against_quota(self, social_account, workspace):
        """Codex P3 regression: an agent could create 100 LinkedIn drafts
        on day 1, wait > 24h, then schedule them all — the quota check
        used to look at ``created_at`` (> 24h ago, outside window) and
        let every row through.
        """
        # Simulate a draft created 25h ago.
        old_post = Post.objects.create(workspace=workspace, caption="old")
        pp = PlatformPost.objects.create(post=old_post, social_account=social_account, status="draft")
        old_time = timezone.now() - timedelta(hours=25)
        PlatformPost.objects.filter(pk=pp.pk).update(created_at=old_time, updated_at=old_time)
        # Now flip to scheduled today (mirrors what the schedule route
        # would do via ``transition_platform_post``).
        PlatformPost.objects.filter(pk=pp.pk).update(status="scheduled", updated_at=timezone.now())

        # The single newly-scheduled row must be counted.
        assert count_recent_creations(social_account) == 1


# ===========================================================================
# P4 — Platform key map matches actual platform codes
# ===========================================================================


class TestPlatformLimitKeysMatchChoices:
    def test_facebook_resolves_to_200_not_default(self):
        from apps.social_accounts.models import SocialAccount

        # The map's Facebook entry must use the canonical platform code
        # ``"facebook"`` (per ``PlatformCredential.Platform.FACEBOOK``).
        # Codex P4: the previous ``"facebook_page"`` key was a no-op.
        fake = SocialAccount(platform="facebook")
        assert resolve_platform_limit(fake) == 200

    def test_dead_twitter_x_keys_are_gone(self):
        # We never had Twitter/X in PlatformCredential.Platform; those
        # keys were dead code that should not survive cleanup.
        assert "twitter" not in PLATFORM_DAILY_POST_LIMIT
        assert "x" not in PLATFORM_DAILY_POST_LIMIT

    def test_every_key_in_map_is_a_real_platform_choice(self):
        from apps.credentials.models import PlatformCredential

        real_choices = set(PlatformCredential.Platform.values)
        for key in PLATFORM_DAILY_POST_LIMIT:
            assert key in real_choices, (
                f"{key!r} is not in PlatformCredential.Platform.values — either rename it or add the choice"
            )


# ===========================================================================
# P5 — MCP rate-limit charged once per JSON-RPC message, not N+1 for batches
# ===========================================================================


@pytest.mark.django_db
class TestMcpBatchRateLimit:
    def test_batch_of_two_charges_exactly_two_tokens(self, owner_client, owner_key, monkeypatch):
        """Codex P5 regression: the top-of-endpoint
        ``enforce_http_rate_limits`` and the per-message loop both ran,
        so a batch of N messages cost N+1 tokens. After the fix the cost
        is exactly N.
        """
        from apps.api import limits as _limits

        calls = {"n": 0}

        def _counting(request, *, is_write):
            calls["n"] += 1

        monkeypatch.setattr(_limits, "enforce_http_rate_limits", _counting)
        # Also monkeypatch the symbol the transport module already imported.
        import apps.mcp.transport as _t

        monkeypatch.setattr(_t, "enforce_http_rate_limits", _counting)

        owner_client.post(
            "/api/v1/mcp/",
            data=json.dumps(
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                    {"jsonrpc": "2.0", "id": 2, "method": "ping"},
                ]
            ),
            content_type="application/json",
        )
        assert calls["n"] == 2, f"expected 1 charge per message (2 total), got {calls['n']}"

    def test_single_message_charges_exactly_one_token(self, owner_client, monkeypatch):
        from apps.api import limits as _limits

        calls = {"n": 0}

        def _counting(request, *, is_write):
            calls["n"] += 1

        monkeypatch.setattr(_limits, "enforce_http_rate_limits", _counting)
        import apps.mcp.transport as _t

        monkeypatch.setattr(_t, "enforce_http_rate_limits", _counting)

        owner_client.post(
            "/api/v1/mcp/",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            content_type="application/json",
        )
        assert calls["n"] == 1


# ===========================================================================
# P6 — Malformed UUID returns empty/422 instead of 500
# ===========================================================================


@pytest.mark.django_db
class TestMalformedUuidHandling:
    def test_workspace_options_partial_handles_bad_uuid(self, client, user):
        """Codex P6 regression: Django UUIDField raises ``ValidationError``,
        not ``ValueError``, so the previous narrower catch let bad UUIDs
        bubble up as 500. Now the cascade returns the empty body it would
        return for a missing/foreign workspace.
        """
        client.force_login(user)
        r = client.get(
            "/organizations/api-keys/_workspace-options/",
            {"workspace_id": "not-a-uuid"},
        )
        assert r.status_code == 200
        assert r.content == b""

    def test_issue_form_handles_bad_uuid(self, client, user):
        client.force_login(user)
        r = client.post(
            "/organizations/api-keys/issue/",
            {
                "name": "bad-uuid",
                "workspace_id": "not-a-uuid",
                "social_account_ids": ["00000000-0000-0000-0000-000000000000"],
            },
            follow=True,
        )
        # Redirects to list with an error message — not a 500.
        assert r.status_code == 200
        assert b"not in this organisation" in r.content


# ===========================================================================
# Codex PR #53 round-2 — Idempotency-Key HTTP header is honoured
# ===========================================================================


@pytest.mark.django_db
class TestIdempotencyKeyHeader:
    """Stripe-style ``Idempotency-Key`` request headers must be honoured
    by the create route, not just the body field. Codex review (PR #53)
    found that a client using only the header would have its idempotency
    silently dropped — every retry-after-timeout created a new post.
    """

    def test_same_header_same_body_replays(self, owner_client, social_account):
        body = {
            "social_account_id": str(social_account.id),
            "caption": "header-keyed write",
            "action": "draft",
        }
        r1 = owner_client.post(
            "/api/v1/posts/",
            data=json.dumps(body),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="header-abc",
        )
        assert r1.status_code == 201
        r2 = owner_client.post(
            "/api/v1/posts/",
            data=json.dumps(body),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="header-abc",
        )
        # Same response replayed — only ONE Post created.
        assert r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]
        assert Post.objects.count() == 1

    def test_body_field_takes_precedence_when_both_present(self, owner_client, social_account):
        """If a caller sends both, the body field wins. Documents the
        deliberate choice in the route comment.
        """
        body_a = {
            "social_account_id": str(social_account.id),
            "caption": "from body key A",
            "action": "draft",
            "idempotency_key": "body-A",
        }
        r1 = owner_client.post(
            "/api/v1/posts/",
            data=json.dumps(body_a),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="header-DIFFERENT",
        )
        assert r1.status_code == 201
        post_a_id = r1.json()["id"]

        # Replay using body key A but a different header — still replays
        # because the body field wins.
        r2 = owner_client.post(
            "/api/v1/posts/",
            data=json.dumps(body_a),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="header-ALSO-DIFFERENT",
        )
        assert r2.status_code == 201
        assert r2.json()["id"] == post_a_id


# ===========================================================================
# Codex PR #53 round-2 — MCP cancel_post is atomic across multi-child posts
# ===========================================================================


@pytest.mark.django_db
class TestMcpCancelAtomic:
    """MCP ``cancel_post`` used to iterate ``transition_platform_post``
    over scheduled children without an outer ``transaction.atomic``, so a
    mid-loop failure left an earlier child in ``draft`` while later
    children stayed ``scheduled``. The REST route already wraps the same
    loop atomically — this test locks in parity for MCP.
    """

    def test_partial_failure_rolls_back(
        self, owner_client, owner_key, workspace, social_account, second_account, user, monkeypatch
    ):
        # Multi-account post: both children scheduled, the SECOND
        # transition raises mid-loop.
        owner_key.api_key.social_accounts.add(second_account)
        post = Post.objects.create(workspace=workspace, author=user, caption="multi")
        PlatformPost.objects.create(
            post=post,
            social_account=social_account,
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(hours=1),
        )
        PlatformPost.objects.create(
            post=post,
            social_account=second_account,
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(hours=1),
        )

        from apps.composer import services as composer_services

        call_count = {"n": 0}
        original = composer_services.transition_platform_post

        def flaky(pp, target_status, **kw):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise ValueError("simulated second-child failure")
            return original(pp, target_status, **kw)

        monkeypatch.setattr("apps.mcp.handlers.transition_platform_post", flaky)

        r = owner_client.post(
            "/api/v1/mcp/",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "cancel_post",
                        "arguments": {"post_id": str(post.id)},
                    },
                }
            ),
            content_type="application/json",
        )
        # JSON-RPC error envelope, but the key claim is the DB state.
        assert "error" in r.json()
        statuses = list(post.platform_posts.values_list("status", flat=True))
        assert all(s == "scheduled" for s in statuses), f"expected all scheduled after rollback, got {statuses}"


@pytest.fixture
def second_account(db, workspace):
    """Second SocialAccount in the same workspace — used to build a
    multi-child post for the MCP cancel atomic test.
    """
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-r2-second",
        account_name="Second LinkedIn R2",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


# ===========================================================================
# Codex PR #53 round-3 — Header idempotency keys are released on errors
# ===========================================================================


@pytest.mark.django_db
class TestHeaderIdempotencyKeyReleasedOnError:
    """If the create path fails AFTER claiming an idempotency slot, the
    release call must use the *effective* key (header fallback applied),
    not ``payload.idempotency_key``. Otherwise a header-only client's
    claim leaks as PENDING and every retry 409s until the 24h sweep
    deletes the row. Codex PR #53 round-3 caught this regression in the
    fix to honour the header.
    """

    def test_failed_create_with_header_key_releases_claim(self, owner_client, owner_key):
        """Trigger a 422 by sending action='schedule' without scheduled_at;
        the route claims the slot, fails, and must release.
        """
        from apps.api.middleware import PENDING_STATUS_SENTINEL
        from apps.api.models import IdempotencyRecord
        from apps.social_accounts.models import SocialAccount

        # Force a post-claim failure path: an account that's disconnected
        # makes create_post raise ValueError, which fires the error
        # release branch (not the pre-claim 422 path).
        sa = SocialAccount.objects.filter(workspace=owner_key.api_key.workspace).first()
        assert sa is not None
        sa.connection_status = SocialAccount.ConnectionStatus.DISCONNECTED
        sa.save()

        body = {
            "social_account_id": str(sa.id),
            "caption": "should fail post-claim",
            "action": "draft",
            # NO body field — relying on header.
        }
        r = owner_client.post(
            "/api/v1/posts/",
            data=json.dumps(body),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="header-release-test",
        )
        assert r.status_code == 422
        # No phantom PENDING row should linger — the release branch ran.
        assert not IdempotencyRecord.objects.filter(
            api_key=owner_key.api_key,
            key="header-release-test",
            response_status=PENDING_STATUS_SENTINEL,
        ).exists(), "PENDING placeholder leaked; the release path didn't see the header key"


# ===========================================================================
# Codex PR #53 round-3 — Reverse M2M signal handler covers remove + clear
# ===========================================================================


@pytest.mark.django_db
class TestReverseM2mInvalidation:
    """Codex flagged that the previous signal handler ran a fresh
    ``ApiKey.objects.filter(social_accounts=instance)`` after the M2M
    mutation had already committed — so reverse-direction ``remove``
    and ``clear`` missed the keys that just lost the relation. The
    handler now reads ``pk_set`` for remove and snapshots via
    ``pre_clear`` for clear.
    """

    def test_reverse_remove_invalidates_cache(self, owner_key, social_account):
        from django.core.cache import cache

        from apps.api_keys.services import _active_cache_key, verify_token

        # Prime the cache.
        assert verify_token(owner_key.plaintext_token) is not None
        cache_key = _active_cache_key(owner_key.api_key.lookup_prefix)
        assert cache.get(cache_key) is not None

        # Reverse-direction remove — ``SocialAccount.api_keys.remove(key)``.
        social_account.api_keys.remove(owner_key.api_key)

        # Cache must be busted immediately, not REVOCATION_CACHE_TTL later.
        assert cache.get(cache_key) is None, (
            "reverse SocialAccount.api_keys.remove() didn't bust the row "
            "cache; pk_set wasn't used in the post_remove handler"
        )

    def test_reverse_clear_invalidates_cache(self, owner_key, social_account):
        from django.core.cache import cache

        from apps.api_keys.services import _active_cache_key, verify_token

        assert verify_token(owner_key.plaintext_token) is not None
        cache_key = _active_cache_key(owner_key.api_key.lookup_prefix)
        assert cache.get(cache_key) is not None

        # Reverse-direction clear — strips every ApiKey relation on the
        # account in one shot.
        social_account.api_keys.clear()

        assert cache.get(cache_key) is None, (
            "reverse SocialAccount.api_keys.clear() didn't bust the row cache; pre_clear snapshot wasn't used"
        )


# ===========================================================================
# Codex PR #53 round-4 — PATCH scheduled_at requires publish_directly on
# already-scheduled posts (privilege escalation: instant-publish + content-burial)
# ===========================================================================


@pytest.mark.django_db
class TestPatchScheduledAtRequiresPublishDirectly:
    """The security review caught that `PATCH /api/v1/posts/{id}` only
    enforced `create_posts`, but it accepted `scheduled_at` and pushed it
    onto every scheduled child via `scheduled_children.update(...)`. A
    key with only `create_posts` could therefore (a) push an admin-
    scheduled post to "now" so the publisher fires it on the next ~15s
    tick — instant publish without `publish_directly`, OR (b) push it to
    year 2099 to silently bury admin-approved content. Both are
    privilege-boundary violations because the create / schedule routes
    and every MCP transition tool gate this exact mutation on
    `publish_directly`.
    """

    def test_patch_scheduled_at_on_scheduled_post_requires_publish_directly(
        self, write_only_client, write_only_membership, workspace, social_account
    ):
        # Admin pre-schedules a post (bypassing HTTP perm checks so we
        # can isolate the PATCH route's gate).
        original_when = timezone.now() + timedelta(days=7)
        post = Post.objects.create(workspace=workspace, caption="admin scheduled")
        pp = PlatformPost.objects.create(
            post=post,
            social_account=social_account,
            status="scheduled",
            scheduled_at=original_when,
        )

        # Editor-scope key (create_posts only) tries to push it to "now".
        when_now = timezone.now().isoformat()
        r = write_only_client.patch(
            f"/api/v1/posts/{post.id}",
            data=json.dumps({"scheduled_at": when_now}),
            content_type="application/json",
        )
        assert r.status_code == 403
        assert "publish_directly" in r.json()["detail"]

        # And the DB row is unchanged — no silent partial commit.
        pp.refresh_from_db()
        assert pp.scheduled_at == original_when
        assert pp.status == "scheduled"

    def test_patch_caption_only_on_scheduled_post_still_allowed(
        self, write_only_client, write_only_membership, workspace, social_account
    ):
        """Editor-scope keys must still be able to edit copy on a
        scheduled post (the legitimate "fix a typo before it publishes"
        flow). Only `scheduled_at` mutations need the elevated permission.
        """
        post = Post.objects.create(workspace=workspace, caption="original")
        PlatformPost.objects.create(
            post=post,
            social_account=social_account,
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(days=7),
        )

        r = write_only_client.patch(
            f"/api/v1/posts/{post.id}",
            data=json.dumps({"caption": "typo fixed"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        post.refresh_from_db()
        assert post.caption == "typo fixed"

    def test_patch_scheduled_at_on_draft_only_post_allowed(
        self, write_only_client, write_only_membership, workspace, social_account
    ):
        """The gate fires only when the post has scheduled children. A
        pure draft has no scheduled children for the mutation to affect,
        so the route should still accept the timestamp (it'll just live
        on Post.scheduled_at until the draft is later promoted via a
        path that DOES require publish_directly).
        """
        post = Post.objects.create(workspace=workspace, caption="just a draft")
        PlatformPost.objects.create(post=post, social_account=social_account, status="draft")

        future = (timezone.now() + timedelta(days=1)).isoformat()
        r = write_only_client.patch(
            f"/api/v1/posts/{post.id}",
            data=json.dumps({"scheduled_at": future}),
            content_type="application/json",
        )
        assert r.status_code == 200
