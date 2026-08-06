"""Tests for the Publish page's bulk selection bar and drag-and-drop reschedule.

Both endpoints promote rows into ``scheduled``, which hands them to the
publisher's poll loop — the privilege ``publish_directly`` gates on every other
scheduling surface (the composer's chip transition, ``save_post``'s publish-now
branch, REST ``/schedule``). These tests pin that gate plus the protected-status
skips and the orphan-Post cleanup.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post
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
    auto_org_ids = list(OrgMembership.objects.filter(user=user).values_list("organization_id", flat=True))
    WorkspaceMembership.objects.filter(user=user).delete()
    OrgMembership.objects.filter(user=user).delete()
    Organization.objects.filter(id__in=auto_org_ids).delete()
    return user


class BulkActionBase(TestCase):
    """One workspace, two channels, and the three roles that matter here.

    ``owner`` holds publish_directly + edit_others_posts, ``editor`` holds only
    edit_others_posts, ``contributor`` holds neither.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Bulk Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="Bulk WS")

        self.owner = _make_user("owner@example.com")
        OrgMembership.objects.create(user=self.owner, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.owner, workspace=self.workspace, workspace_role="owner")

        self.editor = _make_user("editor@example.com")
        OrgMembership.objects.create(user=self.editor, organization=self.org, org_role="member")
        WorkspaceMembership.objects.create(user=self.editor, workspace=self.workspace, workspace_role="editor")

        self.contributor = _make_user("contributor@example.com")
        OrgMembership.objects.create(user=self.contributor, organization=self.org, org_role="member")
        WorkspaceMembership.objects.create(
            user=self.contributor, workspace=self.workspace, workspace_role="contributor"
        )

        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="bluesky",
            account_platform_id="did:plc:bulk-1",
            account_name="bsky",
            connection_status="connected",
        )
        self.other_account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-bulk-1",
            account_name="LI",
            connection_status="connected",
        )

    def _pp(self, status, scheduled_at=None, author=None, account=None, post=None):
        """Create (or extend) a Post and return one of its PlatformPost rows."""
        if post is None:
            post = Post.objects.create(
                workspace=self.workspace,
                author=author or self.owner,
                caption="bulk test",
                scheduled_at=scheduled_at,
            )
        return PlatformPost.objects.create(
            post=post,
            social_account=account or self.account,
            status=status,
            scheduled_at=scheduled_at,
        )

    def _bulk(self, action, *pps):
        return self.client.post(
            reverse("calendar:bulk_platform_action", kwargs={"workspace_id": self.workspace.id}),
            data={"action": action, "platform_post_ids": [str(pp.id) for pp in pps]},
        )


class BulkPlatformActionPermissionTests(BulkActionBase):
    """``publish`` is a scheduling action and needs ``publish_directly``."""

    def test_editor_cannot_bulk_publish(self):
        pp = self._pp("draft")
        self.client.force_login(self.editor)

        response = self._bulk("publish", pp)

        self.assertEqual(response.status_code, 403)
        # Load-bearing invariant (not the status code): an editor holds
        # edit_others_posts, so without this gate the row would have gone
        # straight into the publisher's queue and skipped approval entirely.
        pp.refresh_from_db()
        self.assertEqual(pp.status, "draft")
        self.assertIsNone(pp.scheduled_at)

    def test_editor_can_still_bulk_draft(self):
        pp = self._pp("scheduled", scheduled_at=timezone.now() + timedelta(days=1))
        self.client.force_login(self.editor)

        response = self._bulk("draft", pp)

        self.assertEqual(response.status_code, 200)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "draft")
        self.assertIsNone(pp.scheduled_at)

    def test_contributor_cannot_touch_another_authors_post(self):
        pp = self._pp("scheduled", scheduled_at=timezone.now() + timedelta(days=1), author=self.owner)
        self.client.force_login(self.contributor)

        response = self._bulk("draft", pp)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "scheduled")

    def test_contributor_can_draft_their_own_post(self):
        pp = self._pp("scheduled", scheduled_at=timezone.now() + timedelta(days=1), author=self.contributor)
        self.client.force_login(self.contributor)

        response = self._bulk("draft", pp)

        self.assertEqual(response.json()["count"], 1)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "draft")


class BulkPlatformActionPublishTests(BulkActionBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_publish_schedules_a_draft_at_now(self):
        pp = self._pp("draft")
        before = timezone.now()

        response = self._bulk("publish", pp)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "scheduled")
        self.assertGreaterEqual(pp.scheduled_at, before)
        self.assertLessEqual(pp.scheduled_at, timezone.now())

    def test_publish_pulls_an_already_scheduled_row_forward(self):
        """The Queue tab is entirely ``scheduled`` rows.

        ``scheduled → scheduled`` is not a valid transition, so gating the branch
        on ``can_transition_to`` skipped every row in the tab with no feedback.
        """
        future = timezone.now() + timedelta(days=3)
        pp = self._pp("scheduled", scheduled_at=future)
        before = timezone.now()

        response = self._bulk("publish", pp)

        self.assertEqual(response.json()["count"], 1)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "scheduled")
        self.assertGreaterEqual(pp.scheduled_at, before)
        self.assertLessEqual(pp.scheduled_at, timezone.now())

    def test_publish_skips_protected_rows(self):
        published = self._pp("published")
        publishing = self._pp("publishing")

        response = self._bulk("publish", published, publishing)

        self.assertEqual(response.json()["count"], 0)
        published.refresh_from_db()
        publishing.refresh_from_db()
        self.assertEqual(published.status, "published")
        self.assertEqual(publishing.status, "publishing")

    def test_publish_skips_rows_with_no_route_to_scheduled(self):
        # on_hold deliberately has no edge to scheduled — un-hold first.
        on_hold = self._pp("on_hold")

        response = self._bulk("publish", on_hold)

        self.assertEqual(response.json()["count"], 0)
        on_hold.refresh_from_db()
        self.assertEqual(on_hold.status, "on_hold")


class BulkPlatformActionDeleteTests(BulkActionBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_delete_removes_draft_and_skips_published(self):
        draft = self._pp("draft")
        published = self._pp("published")

        response = self._bulk("delete", draft, published)

        self.assertEqual(response.json()["count"], 1)
        self.assertFalse(PlatformPost.objects.filter(id=draft.id).exists())
        # Load-bearing invariant: a published row is history and cascades away
        # its PublishLog records if deleted.
        self.assertTrue(PlatformPost.objects.filter(id=published.id).exists())

    def test_deleting_the_last_row_deletes_the_orphaned_post(self):
        pp = self._pp("draft")
        post_id = pp.post_id

        self._bulk("delete", pp)

        self.assertFalse(Post.objects.filter(id=post_id).exists())

    def test_post_with_a_surviving_sibling_is_kept_and_resynced(self):
        soon = timezone.now() + timedelta(days=1)
        later = timezone.now() + timedelta(days=5)
        first = self._pp("scheduled", scheduled_at=soon)
        second = self._pp("scheduled", scheduled_at=later, account=self.other_account, post=first.post)

        self._bulk("delete", first)

        post = Post.objects.get(id=second.post_id)
        # The parent aggregate follows the earliest surviving child.
        self.assertEqual(post.scheduled_at, later)


class SentTabCheckboxTests(BulkActionBase):
    """The Sent tab mixes ``published`` (protected) and ``failed`` rows."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def _sent_html(self):
        response = self.client.get(
            reverse("calendar:publish_tab_sent", kwargs={"workspace_id": self.workspace.id}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_published_row_has_no_checkbox(self):
        pp = self._pp("published")
        html = self._sent_html()

        # The row is listed...
        self.assertIn(str(pp.post_id), html)
        # ...but every bulk action skips protected rows, so a checkbox here
        # could only ever be a no-op.
        self.assertNotIn(f"$store.sel.toggle('{pp.id}')", html)

    def test_failed_row_keeps_its_checkbox(self):
        pp = self._pp("failed")

        # `failed` is not protected — bulk retry (publish) and delete both work.
        self.assertIn(f"$store.sel.toggle('{pp.id}')", self._sent_html())


class ReschedulePermissionTests(BulkActionBase):
    """Drag-and-drop promotes draft/failed chips to ``scheduled``."""

    def _reschedule(self, pp, when):
        return self.client.post(
            reverse("calendar:reschedule", kwargs={"workspace_id": self.workspace.id}),
            data={"platform_post_id": str(pp.id), "new_datetime": when.strftime("%Y-%m-%dT%H:%M:%S")},
        )

    def test_editor_cannot_drag_a_draft_chip(self):
        pp = self._pp("draft")
        self.client.force_login(self.editor)

        response = self._reschedule(pp, timezone.now() + timedelta(days=2))

        self.assertEqual(response.status_code, 403)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "draft")
        self.assertIsNone(pp.scheduled_at)

    def test_editor_cannot_drag_a_failed_chip(self):
        pp = self._pp("failed")
        self.client.force_login(self.editor)

        response = self._reschedule(pp, timezone.now() + timedelta(days=2))

        self.assertEqual(response.status_code, 403)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "failed")

    def test_editor_can_still_move_an_approved_chip(self):
        """The gate is narrow: statuses that only re-time are unaffected."""
        pp = self._pp("approved", scheduled_at=timezone.now() + timedelta(days=1))
        self.client.force_login(self.editor)

        response = self._reschedule(pp, timezone.now() + timedelta(days=4))

        self.assertEqual(response.status_code, 204)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "approved")
        self.assertGreater(pp.scheduled_at, timezone.now() + timedelta(days=3))

    def test_owner_dragging_a_draft_schedules_it(self):
        pp = self._pp("draft")
        self.client.force_login(self.owner)

        response = self._reschedule(pp, timezone.now() + timedelta(days=2))

        self.assertEqual(response.status_code, 204)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "scheduled")
        self.assertGreater(pp.scheduled_at, timezone.now() + timedelta(days=1))

    def test_published_chip_cannot_be_rescheduled(self):
        pp = self._pp("published")
        self.client.force_login(self.owner)

        response = self._reschedule(pp, timezone.now() + timedelta(days=2))

        self.assertEqual(response.status_code, 400)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "published")
