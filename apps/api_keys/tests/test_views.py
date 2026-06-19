"""Phase 4 — org-level API key UI views.

Covers:
  * List page renders for an org admin and 403s for a member.
  * The HTMX cascade returns the right accounts + grantable permissions
    for the picked workspace.
  * Issuance happy path renders the one-time reveal modal and creates an
    ``ApiKey`` row.
  * Issuance enforces server-side that workspace + accounts belong to
    the caller's org (tamper resistance).
  * Revoke flips ``revoked_at`` and surfaces 404 for foreign-org keys.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.api_keys.models import ApiKey
from apps.members.models import (
    PERMISSION_KEYS,
    OrgMembership,
    WorkspaceMembership,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="ui-admin@example.com",
        password="testpass123",
        name="UI Admin",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def member_user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="ui-member@example.com",
        password="testpass123",
        name="UI Member",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(admin_user):
    """Use the OrgMembership auto-created by ``apps.accounts.signals`` so
    that RBACMiddleware picks the same one our tests do. Creating a
    second ``Organization`` here would diverge from the real signup
    flow — the middleware uses ``.first()`` and would resolve the
    auto-created "My Organization" instead, breaking every workspace
    lookup downstream.
    """
    return admin_user.org_memberships.first().organization


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="UI Workspace", organization=organization)


@pytest.fixture
def admin_memberships(db, admin_user, organization, workspace):
    # OrgMembership is already created by the signup signal — no need
    # to add a second one. We only need the WorkspaceMembership.
    return WorkspaceMembership.objects.create(
        user=admin_user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )


@pytest.fixture
def member_membership(db, member_user):
    """Downgrade ``member_user``'s auto-created OrgMembership to MEMBER.

    They live in their own ``My Organization`` (the signup signal made
    one). For the "forbidden" check we don't need them in admin's org —
    just somewhere where they lack ``manage_api_keys``.
    """
    membership = member_user.org_memberships.first()
    membership.org_role = OrgMembership.OrgRole.MEMBER
    membership.save(update_fields=["org_role"])
    return membership


@pytest.fixture
def social_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-ui",
        account_name="LinkedIn UI",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


@pytest.fixture
def disconnected_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-broken",
        account_name="Broken LinkedIn",
        connection_status=SocialAccount.ConnectionStatus.DISCONNECTED,
    )


@pytest.fixture
def admin_client(client, admin_user, admin_memberships):
    client.force_login(admin_user)
    return client


@pytest.fixture
def member_client(client, member_user, member_membership):
    client.force_login(member_user)
    return client


# ---------------------------------------------------------------------------
# List page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListPage:
    def test_admin_can_view_list(self, admin_client):
        r = admin_client.get(reverse("api_keys:list"))
        assert r.status_code == 200
        assert b"API Keys" in r.content
        # Empty state — no rows yet.
        assert b"No API keys issued yet." in r.content

    def test_active_key_row_uses_modal_not_native_confirm(self, admin_client, admin_user, workspace, social_account):
        """An active key renders the Alpine revoke-confirmation modal rather
        than the old native ``confirm()`` dialog.

        ``_key_row.html`` is the only place an active row is rendered, and no
        other test exercised it — this guards both the CSP-safe modal markup
        (Alpine directives, no inline ``on*`` handlers) and the removal of the
        ``confirm()`` call.
        """
        from apps.api_keys import services

        services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=admin_user,
            name="render-me",
            permissions=[],
        )
        r = admin_client.get(reverse("api_keys:list"))
        assert r.status_code == 200
        html = r.content.decode()
        # The active row and its teleported confirmation modal rendered.
        assert "render-me" in html
        assert "showRevokeModal" in html
        assert 'x-teleport="body"' in html
        assert "Revoke key" in html  # modal's submit button
        # The native confirm() dialog wiring is gone.
        assert "if (confirm(" not in html
        # The explanatory comment must NOT leak into the page. A multi-line
        # ``{# #}`` comment renders as literal text (Django only treats the
        # hash form as a comment on a single line); here that stray text also
        # became a flex child that squeezed the chip column.
        assert "Alpine-driven confirmation modal" not in html

    def test_member_without_manage_api_keys_is_forbidden(self, member_user, member_membership):
        from django.test import Client

        from apps.members.models import has_org_permission

        # Sanity-check: the membership is MEMBER and lacks manage_api_keys.
        assert member_membership.org_role == OrgMembership.OrgRole.MEMBER
        assert not has_org_permission(member_membership, "manage_api_keys")

        c = Client()
        c.force_login(member_user)
        r = c.get(reverse("api_keys:list"))
        assert r.status_code == 403, (
            f"expected 403 but got {r.status_code} — has_org_permission "
            f"is False for this membership, so the decorator should raise"
        )

    def test_anonymous_redirects_to_login(self, client):
        r = client.get(reverse("api_keys:list"))
        # @login_required redirects to the login page.
        assert r.status_code == 302
        assert "/accounts/login" in r.headers["Location"]


# ---------------------------------------------------------------------------
# HTMX cascade — workspace → accounts + permissions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWorkspaceOptionsPartial:
    def test_returns_connected_accounts_only(self, admin_client, workspace, social_account, disconnected_account):
        r = admin_client.get(
            reverse("api_keys:workspace_options"),
            {"workspace_id": str(workspace.id)},
        )
        assert r.status_code == 200
        body = r.content.decode()
        # Connected account appears; disconnected does NOT — so admins
        # can't mint a key against an account known to be broken.
        assert social_account.account_name in body
        assert disconnected_account.account_name not in body

    def test_blank_workspace_id_returns_empty(self, admin_client):
        r = admin_client.get(reverse("api_keys:workspace_options"))
        assert r.status_code == 200
        assert r.content == b""

    def test_foreign_workspace_returns_empty(self, admin_client, db):
        """A workspace in another org must not leak account info."""
        from apps.organizations.models import Organization
        from apps.workspaces.models import Workspace

        other_org = Organization.objects.create(name="Other")
        foreign_ws = Workspace.objects.create(name="Foreign", organization=other_org)
        r = admin_client.get(
            reverse("api_keys:workspace_options"),
            {"workspace_id": str(foreign_ws.id)},
        )
        # Empty body — same UX as "no workspace picked".
        assert r.content == b""

    def test_permissions_intersected_with_issuer(self, admin_client, workspace, social_account):
        """An owner sees every grantable permission; a non-owner doesn't."""
        from apps.api_keys.views import _HIDDEN_FROM_ISSUANCE

        r = admin_client.get(
            reverse("api_keys:workspace_options"),
            {"workspace_id": str(workspace.id)},
        )
        body = r.content.decode()
        # An owner holds every key in PERMISSION_KEYS, but the issuance picker
        # hides keys whose feature hasn't shipped yet (e.g. view_analytics).
        for k in PERMISSION_KEYS:
            if k in _HIDDEN_FROM_ISSUANCE:
                assert k not in body, f"hidden permission {k} should not appear"
            else:
                assert k in body, f"missing permission {k}"


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIssue:
    def test_happy_path_creates_key_and_reveals_token(self, admin_client, workspace, social_account):
        r = admin_client.post(
            reverse("api_keys:issue"),
            {
                "name": "test bot",
                "workspace_id": str(workspace.id),
                "social_account_ids": [str(social_account.id)],
                "permissions": ["create_posts"],
            },
            follow=True,
        )
        # Surface the flash messages so a real error doesn't get hidden
        # behind a generic status assertion.
        assert r.status_code == 200, r.content[:300]
        body = r.content.decode()
        # Reveal modal markers.
        assert "Save this token now." in body
        assert "bb_studio_" in body
        # Row persisted.
        keys = list(ApiKey.objects.filter(workspace=workspace))
        assert len(keys) == 1
        assert keys[0].name == "test bot"
        assert "create_posts" in (keys[0].permissions or [])

    def test_issue_redirects_and_reload_does_not_resurface_or_reissue(self, admin_client, workspace, social_account):
        """Post/Redirect/Get: issuing lands on the list (not the POST
        endpoint), reveals the token exactly once, and a reload neither
        re-shows the modal nor mints a second key.
        """
        payload = {
            "name": "reload bot",
            "workspace_id": str(workspace.id),
            "social_account_ids": [str(social_account.id)],
            "permissions": ["create_posts"],
        }
        # Without follow we can see the redirect itself (PRG).
        r0 = admin_client.post(reverse("api_keys:issue"), payload)
        assert r0.status_code == 302
        assert r0.headers["Location"] == reverse("api_keys:list")
        # And the plaintext token is NOT carried in the redirect URL.
        assert "bb_studio_" not in r0.headers["Location"]

        # Following the redirect reveals the token once.
        r1 = admin_client.get(r0.headers["Location"])
        body1 = r1.content.decode()
        assert "Save this token now." in body1
        assert "bb_studio_" in body1
        assert ApiKey.objects.filter(workspace=workspace).count() == 1

        # Reloading the list page: token was popped, so no modal — and,
        # crucially, no second key was created (the old non-PRG flow
        # re-POSTed and minted a fresh key on every refresh).
        r2 = admin_client.get(reverse("api_keys:list"))
        body2 = r2.content.decode()
        assert "Save this token now." not in body2
        assert "bb_studio_" not in body2
        assert ApiKey.objects.filter(workspace=workspace).count() == 1

    def test_missing_name_is_rejected(self, admin_client, workspace, social_account):
        r = admin_client.post(
            reverse("api_keys:issue"),
            {
                "name": "",
                "workspace_id": str(workspace.id),
                "social_account_ids": [str(social_account.id)],
            },
            follow=True,
        )
        assert r.status_code == 200
        assert ApiKey.objects.count() == 0
        assert b"Name is required" in r.content

    def test_foreign_workspace_is_rejected(self, admin_client, social_account, db):
        """A tampered POST naming a workspace from another org must fail
        defence-in-depth, not just rely on the UI dropdown.
        """
        from apps.organizations.models import Organization
        from apps.workspaces.models import Workspace

        other_org = Organization.objects.create(name="Other")
        foreign_ws = Workspace.objects.create(name="Foreign", organization=other_org)
        r = admin_client.post(
            reverse("api_keys:issue"),
            {
                "name": "tamper",
                "workspace_id": str(foreign_ws.id),
                "social_account_ids": [str(social_account.id)],
            },
            follow=True,
        )
        assert ApiKey.objects.count() == 0
        assert b"not in this organisation" in r.content

    def test_account_outside_workspace_rejected(self, admin_client, workspace, db):
        """Social account from a different workspace must not be accepted
        even if the workspace_id is legitimate.
        """
        from apps.social_accounts.models import SocialAccount
        from apps.workspaces.models import Workspace

        other_ws = Workspace.objects.create(name="Other WS", organization=workspace.organization)
        foreign_sa = SocialAccount.objects.create(
            workspace=other_ws,
            platform="linkedin_personal",
            account_platform_id="li-foreign",
            account_name="Foreign LinkedIn",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        r = admin_client.post(
            reverse("api_keys:issue"),
            {
                "name": "tamper-account",
                "workspace_id": str(workspace.id),
                "social_account_ids": [str(foreign_sa.id)],
            },
            follow=True,
        )
        assert ApiKey.objects.count() == 0
        assert b"do not belong to that workspace" in r.content

    def test_malformed_account_id_redirects_not_500(self, admin_client, workspace, social_account):
        """A tampered, non-UUID ``social_account_ids`` must yield a graceful
        validation error + redirect, not a 500 from UUIDField coercion.
        """
        r = admin_client.post(
            reverse("api_keys:issue"),
            {
                "name": "tamper-uuid",
                "workspace_id": str(workspace.id),
                "social_account_ids": ["not-a-uuid"],
            },
            follow=True,
        )
        assert r.status_code == 200  # followed the redirect — not a 500
        assert b"do not belong to that workspace" in r.content
        assert ApiKey.objects.count() == 0


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRevoke:
    def test_revoke_flips_revoked_at(self, admin_client, admin_user, workspace, social_account):
        from apps.api_keys import services

        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=admin_user,
            name="to-revoke",
            permissions=[],
        )
        r = admin_client.post(
            reverse("api_keys:revoke", args=[issued.api_key.id]),
        )
        assert r.status_code == 302  # redirect back to list
        issued.api_key.refresh_from_db()
        assert issued.api_key.revoked_at is not None

    def test_revoke_foreign_org_key_404s(self, admin_client, admin_user, workspace, social_account, db):
        """Trying to revoke a key in another org must 404, not silently
        succeed and not 500.
        """
        from apps.accounts.models import User
        from apps.api_keys import services
        from apps.organizations.models import Organization
        from apps.social_accounts.models import SocialAccount
        from apps.workspaces.models import Workspace

        other_org = Organization.objects.create(name="Other")
        foreign_ws = Workspace.objects.create(name="Foreign", organization=other_org)
        foreign_user = User.objects.create_user(
            email="foreign@example.com",
            password="testpass123",
            name="Foreign",
            tos_accepted_at=timezone.now(),
        )
        OrgMembership.objects.create(
            user=foreign_user,
            organization=other_org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        WorkspaceMembership.objects.create(
            user=foreign_user,
            workspace=foreign_ws,
            workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
        )
        foreign_sa = SocialAccount.objects.create(
            workspace=foreign_ws,
            platform="linkedin_personal",
            account_platform_id="li-other",
            account_name="Other LinkedIn",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        foreign_key = services.issue_api_key(
            workspace=foreign_ws,
            social_accounts=[foreign_sa],
            issued_by=foreign_user,
            name="other-org-key",
            permissions=[],
        )

        r = admin_client.post(
            reverse("api_keys:revoke", args=[foreign_key.api_key.id]),
        )
        assert r.status_code == 404
        foreign_key.api_key.refresh_from_db()
        assert foreign_key.api_key.revoked_at is None


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEditKey:
    def _issue(self, admin_user, workspace, social_account, permissions):
        from apps.api_keys import services

        return services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=admin_user,
            name="editable",
            permissions=permissions,
        ).api_key

    def test_get_is_not_allowed(self, admin_client, admin_user, workspace, social_account):
        key = self._issue(admin_user, workspace, social_account, [])
        r = admin_client.get(reverse("api_keys:edit", args=[key.id]))
        assert r.status_code == 405

    def test_member_without_manage_api_keys_is_forbidden(self, member_client):
        from uuid import uuid4

        # The decorator runs before the key lookup, so a random id still 403s.
        r = member_client.post(reverse("api_keys:edit", args=[uuid4()]))
        assert r.status_code == 403

    def test_success_updates_permissions_accounts_and_expiry(self, admin_client, admin_user, workspace, social_account):
        from apps.social_accounts.models import SocialAccount

        second = SocialAccount.objects.create(
            workspace=workspace,
            platform="linkedin_personal",
            account_platform_id="li-second-ui",
            account_name="Second UI",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        key = self._issue(admin_user, workspace, social_account, ["create_posts"])
        r = admin_client.post(
            reverse("api_keys:edit", args=[key.id]),
            {
                "permissions": ["approve_posts"],
                "social_account_ids": [str(second.id)],
                "expires_at": "2030-01-01",
            },
        )
        assert r.status_code == 302
        assert r.headers["Location"] == reverse("api_keys:list")
        key.refresh_from_db()
        assert key.permissions == ["approve_posts"]
        assert set(key.social_accounts.values_list("id", flat=True)) == {second.id}
        assert key.expires_at is not None
        assert key.expires_at.year == 2030

    def test_empty_accounts_is_rejected(self, admin_client, admin_user, workspace, social_account):
        key = self._issue(admin_user, workspace, social_account, ["create_posts"])
        r = admin_client.post(
            reverse("api_keys:edit", args=[key.id]),
            {"permissions": ["create_posts"]},  # no social_account_ids
            follow=True,
        )
        assert r.status_code == 200
        assert b"Select at least one connected account" in r.content
        key.refresh_from_db()
        # Unchanged.
        assert key.permissions == ["create_posts"]
        assert set(key.social_accounts.values_list("id", flat=True)) == {social_account.id}

    def test_empty_permissions_is_allowed(self, admin_client, admin_user, workspace, social_account):
        """Submitting no permission checkboxes clears the (grantable) set —
        an empty key is valid. admin_user is a workspace OWNER, so every perm
        is theirs to grant and nothing is preserved."""
        key = self._issue(admin_user, workspace, social_account, ["create_posts"])
        r = admin_client.post(
            reverse("api_keys:edit", args=[key.id]),
            {"social_account_ids": [str(social_account.id)]},  # no permissions
        )
        assert r.status_code == 302
        key.refresh_from_db()
        assert key.permissions == []

    def test_inactive_key_is_rejected(self, admin_client, admin_user, workspace, social_account):
        from apps.api_keys import services

        key = self._issue(admin_user, workspace, social_account, ["create_posts"])
        services.revoke_api_key(key)
        r = admin_client.post(
            reverse("api_keys:edit", args=[key.id]),
            {"permissions": [], "social_account_ids": [str(social_account.id)]},
            follow=True,
        )
        assert r.status_code == 200
        assert b"is not active" in r.content
        key.refresh_from_db()
        # Permissions untouched despite the POST.
        assert key.permissions == ["create_posts"]

    def test_cross_org_key_404s(self, admin_client, db):
        from apps.accounts.models import User
        from apps.api_keys import services
        from apps.organizations.models import Organization
        from apps.social_accounts.models import SocialAccount
        from apps.workspaces.models import Workspace

        other_org = Organization.objects.create(name="Other")
        foreign_ws = Workspace.objects.create(name="Foreign", organization=other_org)
        foreign_user = User.objects.create_user(
            email="foreign-edit@example.com",
            password="testpass123",
            name="Foreign Edit",
            tos_accepted_at=timezone.now(),
        )
        OrgMembership.objects.create(user=foreign_user, organization=other_org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=foreign_user,
            workspace=foreign_ws,
            workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
        )
        foreign_sa = SocialAccount.objects.create(
            workspace=foreign_ws,
            platform="linkedin_personal",
            account_platform_id="li-foreign-edit",
            account_name="Foreign Edit LinkedIn",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        foreign_key = services.issue_api_key(
            workspace=foreign_ws,
            social_accounts=[foreign_sa],
            issued_by=foreign_user,
            name="other-org-key",
            permissions=["create_posts"],
        ).api_key

        r = admin_client.post(
            reverse("api_keys:edit", args=[foreign_key.id]),
            {"permissions": [], "social_account_ids": [str(foreign_sa.id)]},
        )
        assert r.status_code == 404
        foreign_key.refresh_from_db()
        assert foreign_key.permissions == ["create_posts"]

    def test_list_renders_edit_modal(self, admin_client, admin_user, workspace, social_account):
        self._issue(admin_user, workspace, social_account, ["create_posts"])
        r = admin_client.get(reverse("api_keys:list"))
        html = r.content.decode()
        assert "showEditModal" in html
        assert "Edit API key" in html
        assert "Save changes" in html
        assert reverse("api_keys:edit", args=[ApiKey.objects.first().id]) in html

    def test_malformed_account_id_redirects_not_500(self, admin_client, admin_user, workspace, social_account):
        """A tampered, non-UUID ``social_account_ids`` must redirect with a
        validation error and leave the key untouched — not 500.
        """
        key = self._issue(admin_user, workspace, social_account, ["create_posts"])
        r = admin_client.post(
            reverse("api_keys:edit", args=[key.id]),
            {"permissions": ["create_posts"], "social_account_ids": ["not-a-uuid"]},
            follow=True,
        )
        assert r.status_code == 200  # followed the redirect — not a 500
        assert b"do not belong to that workspace" in r.content
        key.refresh_from_db()
        assert key.permissions == ["create_posts"]
        assert set(key.social_accounts.values_list("id", flat=True)) == {social_account.id}
