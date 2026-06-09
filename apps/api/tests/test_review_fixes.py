"""Regression tests for the 15 issues surfaced in the max-effort code review.

Each test block names the finding it covers so the connection between
review verdict and the change is searchable from either side.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.api.limits import resolve_platform_limit
from apps.api.middleware import _client_ip
from apps.api_keys import services
from apps.api_keys.models import ApiKeyAuditLog
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

    return User.objects.create_user(
        email="fix-owner@example.com",
        password="testpass123",
        name="Fix Owner",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Fix Org")


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
        account_platform_id="li-fix",
        account_name="LinkedIn Fix",
        connection_status="connected",
    )


@pytest.fixture
def second_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-fix-2",
        account_name="LinkedIn Fix 2",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="fix",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


# ===========================================================================
# Finding #14 — `if override:` treated 0 as no override
# ===========================================================================


@pytest.mark.django_db
class TestZeroOverrideHonored:
    def test_zero_daily_post_limit_override_locks_account(self, social_account):
        social_account.daily_post_limit_override = 0
        social_account.save()
        # Codex regression: previously fell through to the LinkedIn default
        # of 100/day. With the fix, 0 IS the cap.
        assert resolve_platform_limit(social_account) == 0


# ===========================================================================
# Finding #15 — HTTPS guard now feeds the throttle, returns generic 401
# ===========================================================================


@pytest.mark.django_db
class TestHttpsGuardFeedsThrottle:
    def test_http_request_returns_401_not_fingerprintable_400(self, issued_key):
        """Codex review: 'Agent API requires HTTPS.' was a free product
        fingerprint AND uncounted toward the throttle. The fix returns
        the same opaque 401 as any other failed auth, and increments
        the IP counter.
        """
        from django.core.cache import cache

        cache.delete("agent_api:auth_fail:127.0.0.1")
        c = Client(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")
        # No secure=True → request.is_secure() is False; DEBUG is False
        # in tests, so the HTTPS guard fires.
        r = c.get("/api/v1/me/")
        assert r.status_code == 401
        # Counter incremented — the next attempt is also 401 and counts.
        # After _AUTH_FAIL_LIMIT (10) failures the IP is locked out.
        assert cache.get("agent_api:auth_fail:127.0.0.1") == 1


# ===========================================================================
# Finding #1 — admin allowlist/permission edits propagate immediately
# ===========================================================================


@pytest.mark.django_db
class TestApiKeyCacheInvalidation:
    def test_removing_social_account_busts_cache_at_next_request(
        self, client_with_token, issued_key, second_account, social_account
    ):
        # Prime the cache via verify_token.
        r = client_with_token.get("/api/v1/me/")
        assert r.status_code == 200

        # Admin adds a NEW account to the allowlist via the M2M. The
        # signal handler should bust the cached row immediately.
        issued_key.api_key.social_accounts.add(second_account)

        r = client_with_token.get("/api/v1/me/")
        ids = {a["id"] for a in r.json()["allowlisted_accounts"]}
        assert str(second_account.id) in ids, (
            "post-edit request still saw the pre-edit allowlist — the m2m_changed signal didn't bust the cache"
        )

        # Now remove the original account — same invariant.
        issued_key.api_key.social_accounts.remove(social_account)
        r = client_with_token.get("/api/v1/me/")
        ids = {a["id"] for a in r.json()["allowlisted_accounts"]}
        assert str(social_account.id) not in ids

    def test_revoke_busts_cache(self, client_with_token, issued_key):
        r = client_with_token.get("/api/v1/me/")
        assert r.status_code == 200
        services.revoke_api_key(issued_key.api_key)
        r = client_with_token.get("/api/v1/me/")
        assert r.status_code == 401


# ===========================================================================
# Finding #2 — X-Forwarded-For only trusted when REMOTE_ADDR is a proxy
# ===========================================================================


@pytest.mark.django_db
class TestTrustedProxyClientIp:
    def test_xff_ignored_when_remote_is_not_in_trusted_list(self, settings):
        from django.test import RequestFactory

        settings.BB_TRUSTED_PROXIES = ()  # no trusted proxies
        req = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="8.8.8.8", REMOTE_ADDR="1.2.3.4")
        # XFF must NOT be honoured — REMOTE_ADDR is the only thing the
        # socket layer attests, so that's what we record / throttle on.
        assert _client_ip(req) == "1.2.3.4"

    def test_xff_honoured_when_remote_is_trusted(self, settings):
        from django.test import RequestFactory

        settings.BB_TRUSTED_PROXIES = ("10.0.0.1",)
        req = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="8.8.8.8, 10.0.0.1", REMOTE_ADDR="10.0.0.1")
        # The proxy is trusted, so XFF is honoured; the leftmost
        # untrusted hop is the originating client.
        assert _client_ip(req) == "8.8.8.8"


# ===========================================================================
# Finding #8 — create_post refuses disconnected SocialAccount
# ===========================================================================


@pytest.mark.django_db
class TestConnectionStatusGate:
    def test_disconnected_account_rejected_by_create_post(self, workspace, owner_memberships, social_account):
        from apps.composer.services import create_post
        from apps.social_accounts.models import SocialAccount

        social_account.connection_status = SocialAccount.ConnectionStatus.DISCONNECTED
        social_account.save()
        with pytest.raises(ValueError, match="connection_status"):
            create_post(
                workspace=workspace,
                social_account=social_account,
                caption="disconnected",
                status="draft",
            )

    def test_error_status_account_rejected_by_create_post(self, workspace, owner_memberships, social_account):
        from apps.composer.services import create_post
        from apps.social_accounts.models import SocialAccount

        social_account.connection_status = SocialAccount.ConnectionStatus.ERROR
        social_account.save()
        with pytest.raises(ValueError, match="connection_status"):
            create_post(
                workspace=workspace,
                social_account=social_account,
                caption="errored",
                status="draft",
            )


# ===========================================================================
# Finding #3 — approval_workflow_mode blocks direct scheduling
# ===========================================================================


@pytest.mark.django_db
class TestApprovalWorkflowGate:
    def test_required_internal_blocks_direct_schedule(self, workspace, owner_memberships, social_account):
        from apps.composer.services import create_post

        workspace.approval_workflow_mode = "required_internal"
        workspace.save()
        with pytest.raises(ValueError, match="approval"):
            create_post(
                workspace=workspace,
                social_account=social_account,
                caption="should require approval",
                scheduled_at=timezone.now() + timedelta(hours=1),
                status="scheduled",
            )

    def test_required_internal_allows_draft(self, workspace, owner_memberships, social_account):
        from apps.composer.services import create_post

        workspace.approval_workflow_mode = "required_internal"
        workspace.save()
        post = create_post(
            workspace=workspace,
            social_account=social_account,
            caption="draft is fine",
            status="draft",
        )
        assert post.pk is not None

    def test_none_workflow_allows_direct_schedule(self, workspace, owner_memberships, social_account):
        from apps.composer.services import create_post

        workspace.approval_workflow_mode = "none"
        workspace.save()
        post = create_post(
            workspace=workspace,
            social_account=social_account,
            caption="no approval needed",
            scheduled_at=timezone.now() + timedelta(hours=1),
            status="scheduled",
        )
        assert post.platform_posts.first().status == "scheduled"


# ===========================================================================
# Finding #6 — PATCH validates media BEFORE writing scheduled_at
# Finding #7 — PATCH media replacement is atomic
# ===========================================================================


@pytest.fixture
def scheduled_post(db, social_account, user, workspace):
    p = Post.objects.create(workspace=workspace, author=user, caption="initial")
    PlatformPost.objects.create(
        post=p,
        social_account=social_account,
        status="scheduled",
        scheduled_at=timezone.now() + timedelta(hours=1),
    )
    return p


@pytest.mark.django_db
class TestPatchAtomicity:
    def test_422_on_foreign_media_does_not_commit_scheduled_at_change(self, client_with_token, scheduled_post):
        """Codex regression: scheduled_children.update() ran BEFORE media
        validation, so a 422 from a foreign media UUID committed the new
        schedule timestamp anyway. The fix validates first, then mutates
        inside an atomic block.
        """
        original_pp = scheduled_post.platform_posts.first()
        original_scheduled_at = original_pp.scheduled_at

        import uuid as _uuid

        new_time = (timezone.now() + timedelta(hours=5)).isoformat()
        r = client_with_token.patch(
            f"/api/v1/posts/{scheduled_post.id}",
            data=json.dumps(
                {
                    "scheduled_at": new_time,
                    "media_asset_ids": [str(_uuid.uuid4())],  # foreign UUID
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 422
        # Critically — the schedule is unchanged.
        original_pp.refresh_from_db()
        assert original_pp.scheduled_at == original_scheduled_at


# ===========================================================================
# Finding #10 — schedule/cancel atomic across multi-child loop
# ===========================================================================


@pytest.fixture
def two_draft_children(db, social_account, second_account, user, workspace, issued_key):
    """Post with two draft children targeting two different accounts; both
    in the key's allowlist so the route accepts it.
    """
    issued_key.api_key.social_accounts.add(second_account)
    p = Post.objects.create(workspace=workspace, author=user, caption="multi")
    PlatformPost.objects.create(post=p, social_account=social_account, status="draft")
    PlatformPost.objects.create(post=p, social_account=second_account, status="draft")
    return p


@pytest.mark.django_db
class TestScheduleAtomic:
    def test_partial_failure_rolls_back_first_child(self, client_with_token, two_draft_children, monkeypatch):
        """Force the second child's transition_to to raise. The first
        child must NOT remain scheduled — the route's transaction.atomic
        should roll the whole loop back.
        """
        from apps.composer import services as composer_services

        call_count = {"n": 0}
        original = composer_services.transition_platform_post

        def flaky_transition(pp, target_status, **kw):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise ValueError("simulated second-child failure")
            return original(pp, target_status, **kw)

        monkeypatch.setattr("apps.api.routers.posts.transition_platform_post", flaky_transition)

        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = client_with_token.post(
            f"/api/v1/posts/{two_draft_children.id}/schedule",
            data=json.dumps({"scheduled_at": when}),
            content_type="application/json",
        )
        assert r.status_code == 422
        # All children must still be draft — no partial commit.
        statuses = list(two_draft_children.platform_posts.values_list("status", flat=True))
        assert all(s == "draft" for s in statuses), f"expected all drafts after rollback, got {statuses}"


# ===========================================================================
# Finding #11 — failed authenticated requests produce audit rows
# ===========================================================================


@pytest.mark.django_db
class TestAuditLogOnFailures:
    def test_404_writes_audit_row(self, client_with_token, issued_key):
        """Codex regression: only success paths used to audit-log; an
        authenticated 404 (e.g. allowlist-blocked post lookup) wrote
        nothing. Now the Ninja exception handler centralises this.
        """
        import uuid as _uuid

        before = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).count()
        r = client_with_token.get(f"/api/v1/posts/{_uuid.uuid4()}")
        assert r.status_code == 404
        after = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).count()
        assert after == before + 1
        latest = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key).latest("created_at")
        assert latest.status_code == 404
        assert "post.read" in latest.action

    def test_403_writes_audit_row(self, client_with_token, issued_key):
        """A request that hits ``_resolve_account``'s allowlist 403 still
        leaves a trail.
        """
        import uuid as _uuid

        before = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key, status_code=403).count()
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(_uuid.uuid4()),
                    "caption": "denied",
                    "action": "draft",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 403
        after = ApiKeyAuditLog.objects.filter(api_key=issued_key.api_key, status_code=403).count()
        assert after == before + 1
