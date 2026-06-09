"""Tests for the org-level permission model and ``@require_org_permission``.

Run via ``pytest apps/members/tests/test_org_permissions.py``.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.members.decorators import require_org_permission
from apps.members.models import (
    BUILTIN_ORG_PERMISSIONS,
    ORG_PERMISSION_KEYS,
    OrgMembership,
    has_org_permission,
)
from apps.organizations.models import Organization


def _make_user(email):
    user = User.objects.create_user(
        email=email,
        password="testpass123",
        tos_accepted_at=timezone.now(),
    )
    # The accounts post_save signal auto-provisions a default Org.
    # Clear it so tests start from a clean slate.
    auto_org_ids = list(OrgMembership.objects.filter(user=user).values_list("organization_id", flat=True))
    from apps.members.models import WorkspaceMembership

    WorkspaceMembership.objects.filter(user=user).delete()
    OrgMembership.objects.filter(user=user).delete()
    Organization.objects.filter(id__in=auto_org_ids).delete()
    return user


class OrgPermissionTableTests(TestCase):
    def test_owner_has_all_permissions(self):
        keys = {k for k, _ in ORG_PERMISSION_KEYS}
        self.assertEqual(
            BUILTIN_ORG_PERMISSIONS[OrgMembership.OrgRole.OWNER],
            keys,
        )

    def test_admin_has_all_permissions(self):
        keys = {k for k, _ in ORG_PERMISSION_KEYS}
        self.assertEqual(
            BUILTIN_ORG_PERMISSIONS[OrgMembership.OrgRole.ADMIN],
            keys,
        )

    def test_member_can_use_but_not_manage_billing(self):
        member_perms = BUILTIN_ORG_PERMISSIONS[OrgMembership.OrgRole.MEMBER]
        self.assertIn("use_intelligence", member_perms)
        self.assertNotIn("manage_intelligence_billing", member_perms)

    def test_has_org_permission_none_membership(self):
        self.assertFalse(has_org_permission(None, "use_intelligence"))

    def test_has_org_permission_owner(self):
        user = _make_user("owner@example.com")
        org = Organization.objects.create(name="Acme")
        m = OrgMembership.objects.create(
            user=user,
            organization=org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        self.assertTrue(has_org_permission(m, "use_intelligence"))
        self.assertTrue(has_org_permission(m, "manage_intelligence_billing"))

    def test_has_org_permission_member_blocked_from_billing(self):
        user = _make_user("member@example.com")
        org = Organization.objects.create(name="Acme")
        m = OrgMembership.objects.create(
            user=user,
            organization=org,
            org_role=OrgMembership.OrgRole.MEMBER,
        )
        self.assertTrue(has_org_permission(m, "use_intelligence"))
        self.assertFalse(has_org_permission(m, "manage_intelligence_billing"))


class RequireOrgPermissionDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.org = Organization.objects.create(name="Acme")

        @require_org_permission("manage_intelligence_billing")
        def billing_view(request, *args, **kwargs):
            return HttpResponse(f"ok org={request.org.id} mem={request.org_membership.org_role}")

        @require_org_permission("use_intelligence")
        def tool_view(request, *args, **kwargs):
            return HttpResponse("ok")

        self.billing_view = billing_view
        self.tool_view = tool_view

    def _request_as(self, user, *, org_id):
        req = self.factory.get(f"/orgs/{org_id}/intelligence/")
        req.user = user
        return req

    def test_anonymous_redirected_to_login(self):
        from django.contrib.auth.models import AnonymousUser

        req = self.factory.get(f"/orgs/{self.org.id}/intelligence/")
        req.user = AnonymousUser()
        resp = self.billing_view(req, org_id=self.org.id)
        # @login_required redirects (302) to LOGIN_URL.
        self.assertEqual(resp.status_code, 302)

    def test_owner_admits_billing_view(self):
        user = _make_user("owner@example.com")
        OrgMembership.objects.create(
            user=user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        req = self._request_as(user, org_id=self.org.id)
        resp = self.billing_view(req, org_id=self.org.id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"ok org=", resp.content)

    def test_admin_admits_billing_view(self):
        user = _make_user("admin@example.com")
        OrgMembership.objects.create(
            user=user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.ADMIN,
        )
        req = self._request_as(user, org_id=self.org.id)
        resp = self.billing_view(req, org_id=self.org.id)
        self.assertEqual(resp.status_code, 200)

    def test_member_denied_billing_view(self):
        from django.core.exceptions import PermissionDenied

        user = _make_user("member@example.com")
        OrgMembership.objects.create(
            user=user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.MEMBER,
        )
        req = self._request_as(user, org_id=self.org.id)
        with self.assertRaises(PermissionDenied):
            self.billing_view(req, org_id=self.org.id)

    def test_member_admits_tool_view(self):
        user = _make_user("member@example.com")
        OrgMembership.objects.create(
            user=user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.MEMBER,
        )
        req = self._request_as(user, org_id=self.org.id)
        resp = self.tool_view(req, org_id=self.org.id)
        self.assertEqual(resp.status_code, 200)

    def test_cross_org_membership_rejected(self):
        """User is a member of org A; tries to access a view for org B."""
        from django.core.exceptions import PermissionDenied

        user = _make_user("alice@example.com")
        org_b = Organization.objects.create(name="Other Co")
        OrgMembership.objects.create(
            user=user,
            organization=org_b,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        # Request to org A (self.org), but user only has membership in org_b.
        req = self._request_as(user, org_id=self.org.id)
        with self.assertRaises(PermissionDenied):
            self.billing_view(req, org_id=self.org.id)

    def test_non_member_denied(self):
        from django.core.exceptions import PermissionDenied

        user = _make_user("nobody@example.com")
        # No OrgMembership created.
        req = self._request_as(user, org_id=self.org.id)
        with self.assertRaises(PermissionDenied):
            self.tool_view(req, org_id=self.org.id)

    def test_missing_org_id_in_url_raises(self):
        from django.core.exceptions import PermissionDenied

        user = _make_user("alice@example.com")
        OrgMembership.objects.create(
            user=user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        req = self.factory.get("/no-org-id/")
        req.user = user
        with self.assertRaises(PermissionDenied):
            self.billing_view(req)  # no org_id kwarg

    def test_request_org_attached_for_view(self):
        """Wrapped view sees request.org / request.org_membership populated."""
        user = _make_user("owner@example.com")
        OrgMembership.objects.create(
            user=user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        req = self._request_as(user, org_id=self.org.id)
        resp = self.billing_view(req, org_id=self.org.id)
        self.assertIn(str(self.org.id).encode(), resp.content)
        self.assertIn(b"mem=owner", resp.content)
