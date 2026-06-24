"""Security regression tests for the May-2026 audit.

Covers V2 (hex-color CSS injection), V6 (queue category IDOR), and V7
(missing role check on custom calendar events).
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import CustomCalendarEvent, Queue
from apps.composer.models import ContentCategory
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


def _make_user(email):
    user = User.objects.create_user(
        email=email,
        password="testpass123",
        tos_accepted_at=timezone.now(),
    )
    # The accounts post_save signal auto-provisions a default Organization +
    # Workspace + OrgMembership for every new User. Tests that want to attach
    # the user to a specific org must start from a clean slate, otherwise the
    # RBAC middleware (which does OrgMembership.objects.filter(...).first())
    # may pick the auto-org instead of the test org.
    from apps.members.models import OrgMembership, WorkspaceMembership
    from apps.organizations.models import Organization

    auto_org_ids = list(OrgMembership.objects.filter(user=user).values_list("organization_id", flat=True))
    WorkspaceMembership.objects.filter(user=user).delete()
    OrgMembership.objects.filter(user=user).delete()
    Organization.objects.filter(id__in=auto_org_ids).delete()
    return user


class CalendarEventColorValidationTests(TestCase):
    """V2 + V7: event create/edit require role and reject non-hex colors."""

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.owner = _make_user("owner@example.com")
        OrgMembership.objects.create(user=self.owner, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.owner, workspace=self.workspace, workspace_role="owner")
        self.viewer = _make_user("viewer@example.com")
        OrgMembership.objects.create(user=self.viewer, organization=self.org, org_role="member")
        WorkspaceMembership.objects.create(user=self.viewer, workspace=self.workspace, workspace_role="viewer")

    def test_viewer_cannot_create_event(self):
        self.client.force_login(self.viewer)
        url = reverse("calendar:event_create", kwargs={"workspace_id": self.workspace.id})
        response = self.client.post(
            url,
            data={
                "title": "Launch",
                "start_date": "2026-06-01",
                "end_date": "2026-06-01",
                "color": "#FF0000",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CustomCalendarEvent.objects.exists())

    def test_owner_with_bad_color_is_rejected(self):
        self.client.force_login(self.owner)
        url = reverse("calendar:event_create", kwargs={"workspace_id": self.workspace.id})
        response = self.client.post(
            url,
            data={
                "title": "Launch",
                "start_date": "2026-06-01",
                "end_date": "2026-06-01",
                "color": "red;background-image:url('//evil')",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomCalendarEvent.objects.exists())

    def test_owner_with_good_color_succeeds(self):
        self.client.force_login(self.owner)
        url = reverse("calendar:event_create", kwargs={"workspace_id": self.workspace.id})
        response = self.client.post(
            url,
            data={
                "title": "Launch",
                "start_date": "2026-06-01",
                "end_date": "2026-06-01",
                "color": "#FF0000",
            },
        )
        self.assertLess(response.status_code, 400)
        self.assertEqual(CustomCalendarEvent.objects.count(), 1)

    def test_event_edit_rejects_bad_color(self):
        event = CustomCalendarEvent.objects.create(
            workspace=self.workspace,
            title="Existing",
            start_date="2026-06-01",
            end_date="2026-06-01",
            color="#3B82F6",
            created_by=self.owner,
        )
        self.client.force_login(self.owner)
        url = reverse(
            "calendar:event_edit",
            kwargs={"workspace_id": self.workspace.id, "event_id": event.id},
        )
        response = self.client.post(url, data={"color": "red;url(x)"})
        self.assertEqual(response.status_code, 400)
        event.refresh_from_db()
        self.assertEqual(event.color, "#3B82F6")


class QueueCreateCategoryIdorTests(TestCase):
    """V6: queue_create must validate category_id against the request workspace."""

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.ws_a = Workspace.objects.create(organization=self.org, name="WS-A")
        self.ws_b = Workspace.objects.create(organization=self.org, name="WS-B")
        self.user = _make_user("user@example.com")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.ws_a, workspace_role="owner")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.ws_b, workspace_role="owner")
        self.account = SocialAccount.objects.create(
            workspace=self.ws_a,
            platform="bluesky",
            account_name="bsky",
            account_platform_id="did:plc:test",
            connection_status="connected",
        )
        self.foreign_category = ContentCategory.objects.create(workspace=self.ws_b, name="Foreign", color="#000000")

    def test_foreign_category_id_returns_404(self):
        self.client.force_login(self.user)
        url = reverse("calendar:queue_create", kwargs={"workspace_id": self.ws_a.id})
        response = self.client.post(
            url,
            data={
                "name": "Test Queue",
                "social_account_id": str(self.account.id),
                "category_id": str(self.foreign_category.id),
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Queue.objects.filter(workspace=self.ws_a).exists())

    def test_no_category_creates_queue(self):
        self.client.force_login(self.user)
        url = reverse("calendar:queue_create", kwargs={"workspace_id": self.ws_a.id})
        response = self.client.post(
            url,
            data={
                "name": "Test Queue",
                "social_account_id": str(self.account.id),
            },
        )
        self.assertLess(response.status_code, 400)
        self.assertTrue(Queue.objects.filter(workspace=self.ws_a, name="Test Queue").exists())
