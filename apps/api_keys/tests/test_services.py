"""Phase 1 — token format, hashing, issuance, lookup, revocation.

These tests exercise the security-critical code paths that the Agent API
auth class depends on. If any of these fail the rest of the stack is
untrustworthy.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.api_keys import services
from apps.api_keys.models import ApiKey
from apps.members.models import OrgMembership, WorkspaceMembership


# ---------------------------------------------------------------------------
# Fixtures — minimal org/workspace/account/user scaffold for issuance tests.
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="issuer@example.com",
        password="testpass123",
        name="Issuer",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Test Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Test Workspace", organization=organization)


@pytest.fixture
def other_workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Other Workspace", organization=organization)


@pytest.fixture
def workspace_owner(db, user, workspace, organization):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
    return WorkspaceMembership.objects.create(
        user=user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )


@pytest.fixture
def workspace_viewer(db, organization, workspace):
    """Membership that only has viewer workspace perms — cannot grant
    ``create_posts``. Promoted to org ``admin`` so the workspace-permission
    check is the discriminator in the elevation test (the new org-permission
    gate is exercised separately by ``org_member_with_workspace_role``).
    """
    from apps.accounts.models import User

    u = User.objects.create_user(
        email="viewer@example.com",
        password="testpass123",
        name="Viewer",
        tos_accepted_at=timezone.now(),
    )
    OrgMembership.objects.create(user=u, organization=organization, org_role=OrgMembership.OrgRole.ADMIN)
    return WorkspaceMembership.objects.create(
        user=u,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.VIEWER,
    )


@pytest.fixture
def org_member_with_workspace_owner_role(db, organization, workspace):
    """A regular org member (no ``manage_api_keys``) who is nonetheless a
    workspace OWNER — i.e. rich workspace perms but lacking the org-level
    gate. Used to verify the manage_api_keys check fails before the
    workspace-permission intersection check.
    """
    from apps.accounts.models import User

    u = User.objects.create_user(
        email="org-member@example.com",
        password="testpass123",
        name="Org Member",
        tos_accepted_at=timezone.now(),
    )
    OrgMembership.objects.create(user=u, organization=organization, org_role=OrgMembership.OrgRole.MEMBER)
    return WorkspaceMembership.objects.create(
        user=u,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )


@pytest.fixture
def social_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-123",
        account_name="Test LinkedIn",
    )


@pytest.fixture
def foreign_social_account(db, other_workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=other_workspace,
        platform="linkedin_personal",
        account_platform_id="li-foreign",
        account_name="Foreign LinkedIn",
    )


# ---------------------------------------------------------------------------
# Token format
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTokenFormat:
    def test_round_trip(self, workspace, workspace_owner, social_account):
        """A freshly issued token parses back to the same lookup_prefix."""
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="round-trip",
            permissions=["create_posts"],
        )
        assert issued.plaintext_token.startswith("bb_studio_")
        parsed = services.parse_token(issued.plaintext_token)
        assert parsed is not None
        assert parsed.lookup_prefix == issued.api_key.lookup_prefix

    def test_malformed_tokens_return_none(self):
        assert services.parse_token("") is None
        assert services.parse_token("not-our-prefix") is None
        # Missing lookup
        assert services.parse_token("bb_studio_short") is None
        # Wrong lookup length
        assert services.parse_token("bb_studio_AAAA_xyz") is None
        # Wrong lookup (content-addressed mismatch)
        # 43 chars secret, but lookup is wrong
        bad = "bb_studio_" + ("A" * 43) + "_00000000"
        assert services.parse_token(bad) is None

    def test_two_tokens_have_distinct_secrets(self, workspace, workspace_owner, social_account):
        a = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="a",
            permissions=[],
        )
        b = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="b",
            permissions=[],
        )
        assert a.plaintext_token != b.plaintext_token
        assert a.api_key.lookup_prefix != b.api_key.lookup_prefix
        assert a.api_key.token_hash != b.api_key.token_hash


# ---------------------------------------------------------------------------
# Verification (read path)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVerifyToken:
    def test_valid_token_resolves(self, workspace, workspace_owner, social_account):
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="valid",
            permissions=["create_posts"],
        )
        resolved = services.verify_token(issued.plaintext_token)
        assert resolved is not None
        assert resolved.pk == issued.api_key.pk

    def test_wrong_secret_constant_time_compare_fails(self, workspace, workspace_owner, social_account):
        """Tamper the random part while keeping the lookup; HMAC compare must fail."""
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="tamper",
            permissions=[],
        )
        # parse_token() is content-addressed, so an attacker can't pass an
        # arbitrary mismatched (secret, lookup). The real defense here is the
        # HMAC pepper: even if an attacker finds an 8-hex-char lookup collision
        # (~2^32 work), the HMAC against the server-side pepper won't match.
        # Simulate that path by mutating the stored hash to a known wrong value
        # and confirming verify_token rejects.
        from django.core.cache import cache as _cache

        ApiKey.objects.filter(pk=issued.api_key.pk).update(token_hash="0" * 64)
        _cache.delete(services._active_cache_key(issued.api_key.lookup_prefix))
        assert services.verify_token(issued.plaintext_token) is None

    def test_revoked_token_returns_none(self, workspace, workspace_owner, social_account):
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="rev",
            permissions=[],
        )
        services.revoke_api_key(issued.api_key)
        assert services.verify_token(issued.plaintext_token) is None

    def test_expired_token_returns_none(self, workspace, workspace_owner, social_account):
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="exp",
            permissions=[],
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        # Bust cache so we see the fresh expiry state.
        from django.core.cache import cache as _cache

        _cache.delete(services._active_cache_key(issued.api_key.lookup_prefix))
        assert services.verify_token(issued.plaintext_token) is None

    def test_issuer_loses_workspace_membership_returns_none(
        self, workspace, workspace_owner, social_account
    ):
        """Regression test for Codex P1#2 — the model contract says
        "if they lose membership the key dies on next use"; verify_token
        must enforce that even on an unrevoked, unexpired key.
        """
        from django.core.cache import cache as _cache

        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="offboarded",
            permissions=[],
        )
        # Confirm baseline — key is usable.
        assert services.verify_token(issued.plaintext_token) is not None

        # Offboard the issuer by deleting their workspace membership.
        workspace_owner.delete()
        # Bust the row cache so we don't ride the 30s TTL — the auth-time
        # re-check would still catch it, but the test should be deterministic.
        _cache.delete(services._active_cache_key(issued.api_key.lookup_prefix))

        assert services.verify_token(issued.plaintext_token) is None

    def test_issuer_deleted_returns_none(
        self, workspace, workspace_owner, social_account
    ):
        """If the issuer is hard-deleted, ``issued_by`` is set to NULL by
        ``on_delete=SET_NULL``. verify_token must reject the now-orphaned key.
        """
        from django.core.cache import cache as _cache

        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="orphan",
            permissions=[],
        )
        # Delete the issuer user entirely — FK clears to NULL.
        workspace_owner.user.delete()
        _cache.delete(services._active_cache_key(issued.api_key.lookup_prefix))

        issued.api_key.refresh_from_db()
        assert issued.api_key.issued_by_id is None
        assert services.verify_token(issued.plaintext_token) is None


# ---------------------------------------------------------------------------
# Issuance guardrails — defense against tampered form posts / privilege creep
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIssuanceGuards:
    def test_rejects_account_from_foreign_workspace(
        self, workspace, workspace_owner, social_account, foreign_social_account
    ):
        with pytest.raises(ValueError, match="does not belong to workspace"):
            services.issue_api_key(
                workspace=workspace,
                social_accounts=[social_account, foreign_social_account],
                issued_by=workspace_owner.user,
                name="bad-scope",
                permissions=[],
            )

    def test_rejects_empty_allowlist(self, workspace, workspace_owner):
        with pytest.raises(ValueError, match="at least one"):
            services.issue_api_key(
                workspace=workspace,
                social_accounts=[],
                issued_by=workspace_owner.user,
                name="empty",
                permissions=[],
            )

    def test_rejects_user_with_no_workspace_membership(self, workspace, organization, social_account, db):
        """Org admin (so the manage_api_keys gate passes) but no workspace
        membership in the target workspace — must still fail.
        """
        from apps.accounts.models import User

        stranger = User.objects.create_user(
            email="stranger@example.com",
            password="testpass123",
            name="Stranger",
            tos_accepted_at=timezone.now(),
        )
        OrgMembership.objects.create(
            user=stranger,
            organization=organization,
            org_role=OrgMembership.OrgRole.ADMIN,
        )
        with pytest.raises(ValueError, match="no membership"):
            services.issue_api_key(
                workspace=workspace,
                social_accounts=[social_account],
                issued_by=stranger,
                name="no-membership",
                permissions=[],
            )

    def test_rejects_permission_outside_issuer_grants(self, workspace, workspace_viewer, social_account):
        """A viewer cannot grant ``create_posts`` even via tampered form data."""
        with pytest.raises(ValueError, match="cannot grant permissions they don't hold"):
            services.issue_api_key(
                workspace=workspace,
                social_accounts=[social_account],
                issued_by=workspace_viewer.user,
                name="elevation",
                permissions=["create_posts"],
            )

    def test_owner_can_grant_all_perms(self, workspace, workspace_owner, social_account):
        """An OWNER membership has the full PERMISSION_KEYS set; issuance must succeed."""
        from apps.members.models import PERMISSION_KEYS

        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="all-perms",
            permissions=list(PERMISSION_KEYS),
        )
        assert set(issued.api_key.permissions) == set(PERMISSION_KEYS)

    def test_rejects_issuer_lacking_org_manage_api_keys(
        self, workspace, org_member_with_workspace_owner_role, social_account
    ):
        """Even a workspace OWNER with full workspace perms cannot mint a key
        without the org-level ``manage_api_keys`` permission.

        Regression test for Codex P1#1 — the service must enforce the
        org-permission gate itself, not just rely on the HTTP view decorator.
        """
        with pytest.raises(ValueError, match="manage_api_keys"):
            services.issue_api_key(
                workspace=workspace,
                social_accounts=[social_account],
                issued_by=org_member_with_workspace_owner_role.user,
                name="should-fail",
                permissions=[],
            )

    def test_rejects_issuer_with_no_org_membership_at_all(
        self, workspace, social_account, db
    ):
        """A user who isn't in the org at all can't mint a key either —
        ``has_org_permission(None, ...)`` returns False, so the gate trips
        before we even hit the workspace check.
        """
        from apps.accounts.models import User

        stranger = User.objects.create_user(
            email="no-org@example.com",
            password="testpass123",
            name="No Org",
            tos_accepted_at=timezone.now(),
        )
        with pytest.raises(ValueError, match="manage_api_keys"):
            services.issue_api_key(
                workspace=workspace,
                social_accounts=[social_account],
                issued_by=stranger,
                name="no-org",
                permissions=[],
            )


# ---------------------------------------------------------------------------
# Touch / last_used debounce
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTouchLastUsed:
    def test_first_touch_updates(self, workspace, workspace_owner, social_account):
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="touch",
            permissions=[],
        )
        assert issued.api_key.last_used_at is None
        services.touch_last_used(issued.api_key, ip="127.0.0.1")
        issued.api_key.refresh_from_db()
        assert issued.api_key.last_used_at is not None
        assert issued.api_key.last_used_ip == "127.0.0.1"

    def test_within_debounce_does_not_re_update(self, workspace, workspace_owner, social_account):
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="touch2",
            permissions=[],
        )
        services.touch_last_used(issued.api_key, ip="1.1.1.1")
        issued.api_key.refresh_from_db()
        first = issued.api_key.last_used_at
        # Re-touching immediately should be a no-op (debounced).
        services.touch_last_used(issued.api_key, ip="2.2.2.2")
        issued.api_key.refresh_from_db()
        assert issued.api_key.last_used_at == first
        # IP did not change because no UPDATE was issued.
        assert issued.api_key.last_used_ip == "1.1.1.1"

    def test_debounce_holds_when_called_via_cached_verify_token(
        self, workspace, workspace_owner, social_account
    ):
        """Regression test for Codex P2 — the previous in-memory debounce
        gated on ``api_key.last_used_at``, which is frozen at row-cache
        write time. A second verify_token within the cache TTL would have
        returned a row with stale ``last_used_at=None`` and re-issued the
        UPDATE on every subsequent call. The cache-keyed debounce fixes it.
        """
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=workspace_owner.user,
            name="cached-debounce",
            permissions=[],
        )

        # First request — cache miss path; verify + touch.
        key1 = services.verify_token(issued.plaintext_token)
        assert key1 is not None
        services.touch_last_used(key1, ip="1.1.1.1")

        # Snapshot the DB state after the first touch.
        ApiKey.objects.get(pk=issued.api_key.pk)  # warm autocommit
        snapshot = ApiKey.objects.values("last_used_at", "last_used_ip").get(pk=issued.api_key.pk)
        assert snapshot["last_used_at"] is not None
        assert snapshot["last_used_ip"] == "1.1.1.1"

        # Second request — cache hit returns a pickled copy whose
        # last_used_at is whatever was captured at cache-set time (None).
        # The buggy implementation would issue another UPDATE here.
        key2 = services.verify_token(issued.plaintext_token)
        assert key2 is not None
        # Reproduce the stale view to make the regression mechanism explicit.
        assert key2.last_used_at is None  # frozen at cache-set time, by design
        services.touch_last_used(key2, ip="2.2.2.2")

        after = ApiKey.objects.values("last_used_at", "last_used_ip").get(pk=issued.api_key.pk)
        # DB is untouched between the two calls — debounce held.
        assert after["last_used_at"] == snapshot["last_used_at"]
        assert after["last_used_ip"] == "1.1.1.1"
