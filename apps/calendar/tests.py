"""Tests for the Content Calendar app (T-1A.2)."""

from datetime import time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import PostingSlot
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


class PostingSlotModelTest(TestCase):
    """Test PostingSlot model."""

    def test_day_of_week_choices(self):
        """All 7 days should be available."""
        self.assertEqual(len(PostingSlot.DayOfWeek.choices), 7)
        self.assertEqual(PostingSlot.DayOfWeek.MONDAY, 0)
        self.assertEqual(PostingSlot.DayOfWeek.SUNDAY, 6)

    def test_str_representation(self):
        from apps.social_accounts.models import SocialAccount

        slot = PostingSlot()
        slot.day_of_week = 0
        slot.time = time(9, 0)
        # Use a real SocialAccount instance (unsaved) to satisfy FK descriptor
        account = SocialAccount(account_name="TestAccount", platform="instagram")
        slot.social_account = account
        s = str(slot)
        self.assertIn("Monday", s)
        self.assertIn("09:00", s)

    def test_day_name_property(self):
        slot = PostingSlot()
        slot.day_of_week = 4
        self.assertEqual(slot.day_name, "Friday")


class PostingSlotCrossWorkspaceTests(TestCase):
    """Slot endpoints must scope every mutation to the requesting workspace.

    The workspace-scoped query is the single authority: a slot outside the
    caller's workspace (or already gone) is a uniform no-op that never mutates
    and never leaks existence via a post-lookup membership check. Treating the
    miss as a no-op also makes delete/update idempotent, so a stale grid
    self-heals instead of 404ing.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="a@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org_a = Organization.objects.create(name="Org A")
        self.workspace_a = Workspace.objects.create(organization=self.org_a, name="Workspace A")
        OrgMembership.objects.create(
            user=self.user_a,
            organization=self.org_a,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        WorkspaceMembership.objects.create(
            user=self.user_a,
            workspace=self.workspace_a,
            workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
        )
        self.account_a = SocialAccount.objects.create(
            workspace=self.workspace_a,
            platform="instagram",
            account_platform_id="ig-a",
            account_name="A",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.slot_a = PostingSlot.objects.create(
            social_account=self.account_a,
            day_of_week=0,
            time=time(9, 0),
        )

        # A second workspace and user — completely isolated
        self.user_b = User.objects.create_user(
            email="b@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org_b = Organization.objects.create(name="Org B")
        self.workspace_b = Workspace.objects.create(organization=self.org_b, name="Workspace B")
        OrgMembership.objects.create(
            user=self.user_b,
            organization=self.org_b,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        WorkspaceMembership.objects.create(
            user=self.user_b,
            workspace=self.workspace_b,
            workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
        )

    def test_delete_own_workspace_slot_succeeds(self):
        """Happy path: an owner deletes a slot in their own workspace."""
        self.client.force_login(self.user_a)
        url = reverse(
            "calendar:delete_posting_slot",
            kwargs={"workspace_id": self.workspace_a.id, "slot_id": self.slot_a.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PostingSlot.objects.filter(id=self.slot_a.id).exists())

    def test_delete_slot_belonging_to_different_workspace_is_noop(self):
        """A slot outside the caller's workspace must never be deleted.

        The workspace-scoped query finds nothing, so the endpoint is a uniform
        no-op: it never mutates and never 404-leaks the foreign slot's existence.
        """
        slot_a2 = PostingSlot.objects.create(
            social_account=self.account_a,
            day_of_week=1,
            time=time(10, 0),
        )
        self.client.force_login(self.user_b)
        # User B uses their OWN workspace_id in the URL (auth passes), but the
        # slot_id is from workspace A — the scoped query never finds it.
        url = reverse(
            "calendar:delete_posting_slot",
            kwargs={"workspace_id": self.workspace_b.id, "slot_id": slot_a2.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        # Load-bearing invariant (not the 200 status): the foreign slot is untouched.
        self.assertTrue(PostingSlot.objects.filter(id=slot_a2.id).exists())

    def test_update_slot_belonging_to_different_workspace_is_noop(self):
        """A slot outside the caller's workspace must never be modified."""
        slot_a2 = PostingSlot.objects.create(
            social_account=self.account_a,
            day_of_week=2,
            time=time(11, 0),
        )
        self.client.force_login(self.user_b)
        url = reverse(
            "calendar:update_posting_slot",
            kwargs={"workspace_id": self.workspace_b.id, "slot_id": slot_a2.id},
        )
        response = self.client.post(url, data={"time": "13:30"})
        self.assertEqual(response.status_code, 200)
        # Load-bearing invariant (not the 200 status): the foreign slot is unchanged.
        slot_a2.refresh_from_db()
        self.assertEqual(slot_a2.time, time(11, 0))

    def test_delete_already_gone_slot_is_idempotent_self_heal(self):
        """Re-deleting an own-workspace slot that is already gone refreshes the
        grid (HX-Trigger) instead of 404ing — the stale-page / double-click fix.
        """
        url = reverse(
            "calendar:delete_posting_slot",
            kwargs={"workspace_id": self.workspace_a.id, "slot_id": self.slot_a.id},
        )
        self.client.force_login(self.user_a)
        first = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(first.status_code, 204)
        self.assertIn("slotsUpdated", first.headers.get("HX-Trigger", ""))
        self.assertFalse(PostingSlot.objects.filter(id=self.slot_a.id).exists())
        # Second delete of the now-missing slot must NOT 404; with the posted
        # account id it still emits the grid-refresh trigger so the stale row clears.
        second = self.client.post(
            url, data={"social_account_id": str(self.account_a.id)}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(second.status_code, 204)
        self.assertIn(str(self.account_a.id), second.headers.get("HX-Trigger", ""))

    def test_delete_real_slot_emits_account_scoped_trigger(self):
        """The happy-path HX-Trigger carries the account id under ``detail`` so the
        grid's ``slotsUpdated[detail.accountId==...]`` filter matches and refreshes.
        """
        import json

        url = reverse(
            "calendar:delete_posting_slot",
            kwargs={"workspace_id": self.workspace_a.id, "slot_id": self.slot_a.id},
        )
        self.client.force_login(self.user_a)
        resp = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 204)
        payload = json.loads(resp.headers["HX-Trigger"])
        self.assertEqual(payload["slotsUpdated"]["accountId"], str(self.account_a.id))

    def test_update_already_gone_slot_is_idempotent_self_heal(self):
        """Editing the time of an own-workspace slot that is already gone refreshes
        the grid (HX-Trigger) instead of 404ing — mirrors the delete self-heal.
        """
        url = reverse(
            "calendar:update_posting_slot",
            kwargs={"workspace_id": self.workspace_a.id, "slot_id": self.slot_a.id},
        )
        self.client.force_login(self.user_a)
        self.slot_a.delete()
        resp = self.client.post(
            url,
            data={"time": "08:15", "social_account_id": str(self.account_a.id)},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 204)
        self.assertIn(str(self.account_a.id), resp.headers.get("HX-Trigger", ""))

    def test_slot_mutation_denied_for_member_without_manage_permission(self):
        """A workspace member whose role lacks manage_social_accounts cannot mutate
        posting slots, even though they pass the membership check.
        """
        viewer = User.objects.create_user(
            email="viewer@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        OrgMembership.objects.create(
            user=viewer,
            organization=self.org_a,
            org_role=OrgMembership.OrgRole.MEMBER,
        )
        WorkspaceMembership.objects.create(
            user=viewer,
            workspace=self.workspace_a,
            workspace_role=WorkspaceMembership.WorkspaceRole.VIEWER,
        )
        self.client.force_login(viewer)
        url = reverse(
            "calendar:delete_posting_slot",
            kwargs={"workspace_id": self.workspace_a.id, "slot_id": self.slot_a.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        # The slot must survive an unauthorized delete attempt.
        self.assertTrue(PostingSlot.objects.filter(id=self.slot_a.id).exists())
