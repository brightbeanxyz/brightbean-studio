"""Tests for the Publish page's bulk selection bar and drag-and-drop reschedule.

Both endpoints promote rows into ``scheduled``, which hands them to the
publisher's poll loop — the privilege ``publish_directly`` gates on every other
scheduling surface (the composer's chip transition, ``save_post``'s publish-now
branch, REST ``/schedule``). These tests pin that gate plus the protected-status
skips and the orphan-Post cleanup.
"""

import zoneinfo
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import Queue, QueueEntry
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


class BulkPlatformActionFailedRowTests(BulkActionBase):
    """``failed`` is the status this PR newly made actionable in both paths."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_publish_retries_a_failed_row(self):
        pp = self._pp("failed")
        pp.publish_error = "Instagram: media download timed out"
        pp.retry_count = 3
        pp.next_retry_at = timezone.now() + timedelta(minutes=5)
        pp.save(update_fields=["publish_error", "retry_count", "next_retry_at"])

        response = self._bulk("publish", pp)

        self.assertEqual(response.json()["count"], 1)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "scheduled")
        # Load-bearing invariant: the previous attempt's failure state must not
        # ride along, or the chip renders a stale error and the fresh attempt
        # starts with its retry budget already spent.
        self.assertEqual(pp.publish_error, "")
        self.assertEqual(pp.retry_count, 0)
        self.assertIsNone(pp.next_retry_at)

    def test_draft_unschedules_a_failed_row(self):
        pp = self._pp("failed", scheduled_at=timezone.now() - timedelta(hours=1))

        response = self._bulk("draft", pp)

        self.assertEqual(response.json()["count"], 1)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "draft")
        self.assertIsNone(pp.scheduled_at)

    def test_reschedule_clears_failure_state_on_retry(self):
        pp = self._pp("failed")
        pp.publish_error = "boom"
        pp.retry_count = 2
        pp.save(update_fields=["publish_error", "retry_count"])

        response = self.client.post(
            reverse("calendar:reschedule", kwargs={"workspace_id": self.workspace.id}),
            data={
                "platform_post_id": str(pp.id),
                "new_datetime": (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

        self.assertEqual(response.status_code, 204)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "scheduled")
        self.assertEqual(pp.publish_error, "")
        self.assertEqual(pp.retry_count, 0)


class BulkPlatformActionQueueMirrorTests(BulkActionBase):
    """Bulk actions must keep QueueEntry rows in step, like their siblings do."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)
        self.queue = Queue.objects.create(workspace=self.workspace, name="Q", social_account=self.account)

    def _queued(self, status="scheduled", slot=None):
        slot = slot or timezone.now() + timedelta(days=3)
        pp = self._pp(status, scheduled_at=slot)
        entry = QueueEntry.objects.create(queue=self.queue, post=pp.post, position=0, assigned_slot_datetime=slot)
        return pp, entry

    def test_draft_removes_the_queue_entry(self):
        pp, entry = self._queued()

        self._bulk("draft", pp)

        # remove_from_queue deletes the entry when a post leaves the queue;
        # leaving it behind keeps an unscheduled post listed at its old slot.
        self.assertFalse(QueueEntry.objects.filter(id=entry.id).exists())

    def test_publish_moves_the_queue_entry_forward(self):
        pp, entry = self._queued()
        before = timezone.now()

        self._bulk("publish", pp)

        entry.refresh_from_db()
        self.assertGreaterEqual(entry.assigned_slot_datetime, before)

    def test_deleting_one_child_removes_only_that_channels_entry(self):
        slot = timezone.now() + timedelta(days=3)
        pp, entry = self._queued(slot=slot)
        # A sibling on another channel keeps the parent Post alive, so the FK
        # cascade never fires and the entry must be cleared explicitly.
        self._pp("scheduled", scheduled_at=slot, account=self.other_account, post=pp.post)

        self._bulk("delete", pp)

        self.assertTrue(Post.objects.filter(id=pp.post_id).exists())
        self.assertFalse(QueueEntry.objects.filter(id=entry.id).exists())


class BulkPublishStaggerTests(BulkActionBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_same_channel_rows_are_spaced_apart(self):
        a = self._pp("draft")
        b = self._pp("draft")
        c = self._pp("draft")

        self._bulk("publish", a, b, c)

        times = sorted(PlatformPost.objects.filter(id__in=[a.id, b.id, c.id]).values_list("scheduled_at", flat=True))
        # Posting slots exist to space a channel's output; three posts fired at
        # one account in a single publisher tick invites rate limiting.
        self.assertEqual(len(set(times)), 3)
        self.assertEqual((times[1] - times[0]), timedelta(minutes=1))
        self.assertEqual((times[2] - times[1]), timedelta(minutes=1))

    def test_stagger_follows_the_existing_schedule_order(self):
        """Offsets are handed out in iteration order, so the order must be fixed.

        An unordered ``id__in`` queryset could otherwise assign the later slot to
        the earlier-scheduled post and publish the Queue out of order.
        """
        base = timezone.now() + timedelta(days=1)
        # Created in reverse-schedule order on purpose: insertion order is what
        # an unordered queryset tends to return, so rows whose physical order
        # already matched their schedule would let the bug pass unnoticed.
        third = self._pp("scheduled", scheduled_at=base + timedelta(hours=2))
        second = self._pp("scheduled", scheduled_at=base + timedelta(hours=1))
        first = self._pp("scheduled", scheduled_at=base)

        # Submitted in a third, unrelated order.
        self._bulk("publish", second, third, first)

        for pp in (first, second, third):
            pp.refresh_from_db()
        self.assertLess(first.scheduled_at, second.scheduled_at)
        self.assertLess(second.scheduled_at, third.scheduled_at)

    def test_different_channels_both_start_now(self):
        a = self._pp("draft")
        b = self._pp("draft", account=self.other_account)

        self._bulk("publish", a, b)

        a.refresh_from_db()
        b.refresh_from_db()
        # Spacing is per channel — a second account has no reason to wait.
        self.assertEqual(a.scheduled_at, b.scheduled_at)


class PublishTabCountTests(BulkActionBase):
    """Badge counts must agree with the filtered list they sit above."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_queue_count_respects_the_channel_filter(self):
        soon = timezone.now() + timedelta(days=1)
        self._pp("scheduled", scheduled_at=soon)
        self._pp("scheduled", scheduled_at=soon)
        self._pp("scheduled", scheduled_at=soon, account=self.other_account)

        response = self.client.get(
            reverse("calendar:publish_tab_queue", kwargs={"workspace_id": self.workspace.id}),
            {"channel": str(self.other_account.id)},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["queue_count"], 1)

    def test_unfiltered_queue_count_sees_everything(self):
        soon = timezone.now() + timedelta(days=1)
        self._pp("scheduled", scheduled_at=soon)
        self._pp("scheduled", scheduled_at=soon, account=self.other_account)

        response = self.client.get(
            reverse("calendar:publish_tab_queue", kwargs={"workspace_id": self.workspace.id}),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.context["queue_count"], 2)


class TodayInViewTimezoneTests(BulkActionBase):
    """The Today button must agree with the day the grid highlights."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_today_is_read_in_the_display_timezone(self):
        """At 22:00 UTC it is already tomorrow in Tokyo.

        The grids compute `today` as now-in-display-tz; the toolbar must use the
        same clock or the button disables on the wrong day for hours at a time.
        """
        tokyo = zoneinfo.ZoneInfo("Asia/Tokyo")
        fixed = datetime(2026, 8, 7, 22, 0, tzinfo=UTC)
        tokyo_today = fixed.astimezone(tokyo).date()
        self.assertEqual(tokyo_today, date(2026, 8, 8))  # guards the premise

        url = reverse("calendar:calendar", kwargs={"workspace_id": self.workspace.id})
        with patch("django.utils.timezone.now", return_value=fixed):
            response = self.client.get(
                url, {"mode": "calendar", "view": "day", "date": "2026-08-08", "tz": "Asia/Tokyo"}
            )
            self.assertTrue(response.context["is_today_in_view"])

            response = self.client.get(
                url, {"mode": "calendar", "view": "day", "date": "2026-08-07", "tz": "Asia/Tokyo"}
            )
            self.assertFalse(response.context["is_today_in_view"])


class InvalidTimezoneTests(BulkActionBase):
    """``?tz=`` is raw user input and reaches zoneinfo.ZoneInfo on every path."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_list_mode_survives_a_bogus_timezone(self):
        url = reverse("calendar:calendar", kwargs={"workspace_id": self.workspace.id})

        response = self.client.get(url, {"mode": "list", "tab": "queue", "tz": "Not/AZone"})

        self.assertEqual(response.status_code, 200)
        # Coerced at the source, so every consumer downstream gets a real zone.
        self.assertEqual(response.context["display_timezone"], "UTC")

    def test_calendar_mode_survives_a_bogus_timezone(self):
        url = reverse("calendar:calendar", kwargs={"workspace_id": self.workspace.id})

        for view in ("month", "week", "day"):
            with self.subTest(view=view):
                response = self.client.get(url, {"mode": "calendar", "view": view, "tz": "Not/AZone"})
                self.assertEqual(response.status_code, 200)

    def test_a_real_timezone_is_still_honoured(self):
        url = reverse("calendar:calendar", kwargs={"workspace_id": self.workspace.id})

        response = self.client.get(url, {"mode": "list", "tab": "queue", "tz": "Asia/Tokyo"})

        self.assertEqual(response.context["display_timezone"], "Asia/Tokyo")


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
