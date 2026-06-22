"""Tests for the Content Calendar app (T-1A.2)."""

import zoneinfo
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import PostingSlot, Queue, QueueEntry, RecurrenceRule
from apps.calendar.services import (
    QueueFullError,
    _next_slot_datetimes,
    add_post_next_available,
    add_to_queue,
    prioritize,
    remove_from_queue,
    reorder_queue,
    repair_future_published_scheduled_at,
    reslot_to_next_available,
)
from apps.calendar.tasks import generate_recurring_posts
from apps.calendar.views import _day_view_data
from apps.composer.models import PlatformPost, Post
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
        second = self.client.post(url, data={"social_account_id": str(self.account_a.id)}, HTTP_HX_REQUEST="true")
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


class QueueSlotTimezoneTests(TestCase):
    """Queue slot assignment must resolve PostingSlot times in the workspace
    timezone (which falls back to the org's default_timezone), not UTC.

    Regression for the bug where ``assign_queue_slots`` passed ``timezone.now()``
    (UTC) as the baseline, so a "09:00" slot was scheduled at 09:00 UTC instead
    of 09:00 in the org's local zone.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="TZ Org", default_timezone="America/New_York")
        self.workspace = Workspace.objects.create(organization=self.org, name="TZ WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="instagram",
            account_platform_id="ig-tz",
            account_name="TZ",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.queue = Queue.objects.create(
            workspace=self.workspace,
            name="TZ Queue",
            social_account=self.account,
        )
        # A 09:00 slot on every weekday, so "the next available slot" is always
        # a 09:00 local time no matter what day/time the test actually runs.
        for day in range(7):
            PostingSlot.objects.create(social_account=self.account, day_of_week=day, time=time(9, 0))

    def test_queue_slot_resolved_in_workspace_timezone(self):
        post = Post.objects.create(workspace=self.workspace, caption="queued")
        PlatformPost.objects.create(post=post, social_account=self.account)

        add_to_queue(post, self.queue)

        ny = zoneinfo.ZoneInfo("America/New_York")
        entry = QueueEntry.objects.get(queue=self.queue, post=post)
        self.assertIsNotNone(entry.assigned_slot_datetime)

        local = entry.assigned_slot_datetime.astimezone(ny)
        self.assertEqual((local.hour, local.minute), (9, 0))
        # The stored instant is 09:00 NY expressed in UTC (13:00 EST / 14:00
        # EDT) — never a literal 09:00 UTC, which is the pre-fix bug.
        utc = entry.assigned_slot_datetime.astimezone(zoneinfo.ZoneInfo("UTC"))
        self.assertIn(utc.hour, (13, 14))

        # The per-platform scheduled_at (what the publisher fires on) matches.
        pp = PlatformPost.objects.get(post=post, social_account=self.account)
        self.assertEqual(pp.scheduled_at, entry.assigned_slot_datetime)

    def test_workspace_override_takes_precedence_over_org(self):
        # An explicit workspace timezone overrides the org default.
        self.workspace.timezone = "Asia/Tokyo"
        self.workspace.save(update_fields=["timezone"])
        post = Post.objects.create(workspace=self.workspace, caption="queued-tokyo")
        PlatformPost.objects.create(post=post, social_account=self.account)

        add_to_queue(post, self.queue)

        entry = QueueEntry.objects.get(queue=self.queue, post=post)
        local = entry.assigned_slot_datetime.astimezone(zoneinfo.ZoneInfo("Asia/Tokyo"))
        self.assertEqual((local.hour, local.minute), (9, 0))


class QueueSlotPublishedGuardTests(TestCase):
    """Already-published queue entries must never be re-slotted.

    Regression for the bug where adding/reordering a queue recomputed slots for
    *every* entry — including posts already published — dragging their
    ``scheduled_at`` onto a future slot. The calendar places chips by
    ``scheduled_at``, so those published posts then appeared as "published" a
    week in the future.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Guard Org", default_timezone="UTC")
        self.workspace = Workspace.objects.create(organization=self.org, name="Guard WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-guard",
            account_name="Guard",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.queue = Queue.objects.create(
            workspace=self.workspace,
            name="Guard Queue",
            social_account=self.account,
        )
        # A 09:00 slot every weekday so "the next slot" is always available.
        for day in range(7):
            PostingSlot.objects.create(social_account=self.account, day_of_week=day, time=time(9, 0))

    def _published_entry(self, position):
        last_week = timezone.now() - timedelta(days=7)
        post = Post.objects.create(workspace=self.workspace, caption="already out")
        PlatformPost.objects.create(
            post=post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            scheduled_at=last_week,
            published_at=last_week,
        )
        QueueEntry.objects.create(queue=self.queue, post=post, position=position)
        return post, last_week

    def test_add_to_queue_leaves_published_entry_in_the_past(self):
        published_post, last_week = self._published_entry(position=0)

        live_post = Post.objects.create(workspace=self.workspace, caption="next up")
        PlatformPost.objects.create(
            post=live_post,
            social_account=self.account,
            status=PlatformPost.Status.SCHEDULED,
        )

        # Adding a fresh post recomputes the whole queue's slots.
        add_to_queue(live_post, self.queue)

        # The published post keeps its original (past) schedule — untouched.
        published_pp = PlatformPost.objects.get(post=published_post)
        self.assertEqual(published_pp.scheduled_at, last_week)
        self.assertEqual(published_pp.status, PlatformPost.Status.PUBLISHED)

        # The live post flows into the soonest open future slot — and isn't
        # pushed back a slot by the (now-skipped) published entry ahead of it.
        live_pp = PlatformPost.objects.get(post=live_post)
        self.assertIsNotNone(live_pp.scheduled_at)
        self.assertGreater(live_pp.scheduled_at, timezone.now())
        expected_first = _next_slot_datetimes(self.account, timezone.now(), count=1)[0]
        self.assertEqual(live_pp.scheduled_at, expected_first)

    def test_reorder_queue_does_not_move_published_entry(self):
        published_post, last_week = self._published_entry(position=0)

        live_post = Post.objects.create(workspace=self.workspace, caption="reorder me")
        PlatformPost.objects.create(
            post=live_post,
            social_account=self.account,
            status=PlatformPost.Status.SCHEDULED,
        )
        live_entry = QueueEntry.objects.create(queue=self.queue, post=live_post, position=1)

        reorder_queue(self.queue, [str(live_entry.id)])

        published_pp = PlatformPost.objects.get(post=published_post)
        self.assertEqual(published_pp.scheduled_at, last_week)


class RepairPublishedScheduledAtTests(TestCase):
    """The repair resets only the future-dated published rows, nothing else."""

    def setUp(self):
        self.org = Organization.objects.create(name="Repair Org", default_timezone="UTC")
        self.workspace = Workspace.objects.create(organization=self.org, name="Repair WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-repair",
            account_name="Repair",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.last_week = timezone.now() - timedelta(days=7)
        self.next_week = timezone.now() + timedelta(days=7)

        # Corrupted: published, but scheduled_at dragged a week into the future.
        self.corrupt_post = Post.objects.create(workspace=self.workspace, caption="dragged forward")
        self.corrupt_pp = PlatformPost.objects.create(
            post=self.corrupt_post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            published_at=self.last_week,
            scheduled_at=self.next_week,
        )
        # Healthy published row: scheduled before it published — must be left alone.
        self.healthy_post = Post.objects.create(workspace=self.workspace, caption="published normally")
        self.healthy_pp = PlatformPost.objects.create(
            post=self.healthy_post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            published_at=self.last_week,
            scheduled_at=self.last_week - timedelta(minutes=5),
        )
        # Genuinely scheduled future post (not yet published) — must be left alone.
        self.future_post = Post.objects.create(workspace=self.workspace, caption="still upcoming")
        self.future_pp = PlatformPost.objects.create(
            post=self.future_post,
            social_account=self.account,
            status=PlatformPost.Status.SCHEDULED,
            scheduled_at=self.next_week,
        )

        # The bug also stamped the same future slot onto the QueueEntry; the
        # queue UI reads assigned_slot_datetime, so the repair must reset it too.
        self.queue = Queue.objects.create(
            workspace=self.workspace,
            name="Repair Queue",
            social_account=self.account,
        )
        self.corrupt_entry = QueueEntry.objects.create(
            queue=self.queue,
            post=self.corrupt_post,
            position=0,
            assigned_slot_datetime=self.next_week,
        )
        # A correctly-scheduled queue entry (past slot) must be left alone.
        self.healthy_entry = QueueEntry.objects.create(
            queue=self.queue,
            post=self.healthy_post,
            position=1,
            assigned_slot_datetime=self.last_week - timedelta(minutes=5),
        )

    def test_dry_run_reports_but_writes_nothing(self):
        result = repair_future_published_scheduled_at(apply=False)

        self.assertEqual(result["platform_post_count"], 1)
        self.assertFalse(result["applied"])
        self.assertEqual(result["rows"][0]["platform_post_id"], str(self.corrupt_pp.id))

        # Nothing changed on disk.
        self.corrupt_pp.refresh_from_db()
        self.assertEqual(self.corrupt_pp.scheduled_at, self.next_week)

    def test_apply_snaps_only_the_corrupt_row_to_published_at(self):
        result = repair_future_published_scheduled_at(apply=True)
        self.assertTrue(result["applied"])
        self.assertEqual(result["platform_post_count"], 1)

        # Corrupt row snapped back to its real publish instant.
        self.corrupt_pp.refresh_from_db()
        self.assertEqual(self.corrupt_pp.scheduled_at, self.last_week)
        # Parent aggregate re-synced to match.
        self.corrupt_post.refresh_from_db()
        self.assertEqual(self.corrupt_post.scheduled_at, self.last_week)

        # Healthy + genuinely-future rows untouched.
        self.healthy_pp.refresh_from_db()
        self.assertEqual(self.healthy_pp.scheduled_at, self.last_week - timedelta(minutes=5))
        self.future_pp.refresh_from_db()
        self.assertEqual(self.future_pp.scheduled_at, self.next_week)

    def test_idempotent_second_run_finds_nothing(self):
        repair_future_published_scheduled_at(apply=True)
        again = repair_future_published_scheduled_at(apply=True)
        self.assertEqual(again["platform_post_count"], 0)
        self.assertFalse(again["applied"])

    def test_workspace_scope_excludes_other_workspaces(self):
        other_ws = Workspace.objects.create(organization=self.org, name="Other WS")
        result = repair_future_published_scheduled_at(workspace_id=other_ws.id, apply=True)
        self.assertEqual(result["platform_post_count"], 0)
        self.corrupt_pp.refresh_from_db()
        self.assertEqual(self.corrupt_pp.scheduled_at, self.next_week)

    def test_management_command_applies_repair(self):
        call_command("repair_published_scheduled_at")
        self.corrupt_pp.refresh_from_db()
        self.assertEqual(self.corrupt_pp.scheduled_at, self.last_week)

    def test_repair_resets_stale_queue_entry_slot(self):
        result = repair_future_published_scheduled_at(apply=True)
        self.assertEqual(result["queue_entry_count"], 1)

        # The corrupt entry's queue slot snaps back to the real publish time so
        # queue_detail no longer renders the published post in the future.
        self.corrupt_entry.refresh_from_db()
        self.assertEqual(self.corrupt_entry.assigned_slot_datetime, self.last_week)
        # A correctly-scheduled queue entry is untouched.
        self.healthy_entry.refresh_from_db()
        self.assertEqual(self.healthy_entry.assigned_slot_datetime, self.last_week - timedelta(minutes=5))

    def test_dry_run_counts_stale_queue_entry_without_writing(self):
        result = repair_future_published_scheduled_at(apply=False)
        self.assertEqual(result["queue_entry_count"], 1)
        self.corrupt_entry.refresh_from_db()
        self.assertEqual(self.corrupt_entry.assigned_slot_datetime, self.next_week)

    def test_repair_does_not_make_fallback_scheduled_sibling_due(self):
        """A still-scheduled sibling that rides the parent fallback must not be
        dragged into the past (and published early) when the repair lowers the
        parent aggregate.

        Multi-platform post: one child already published (with its scheduled_at
        dragged into the future) and a sibling on another account still
        SCHEDULED with no scheduled_at of its own — the sibling's due time
        resolves through the publisher's
        ``Coalesce(scheduled_at, post__scheduled_at)`` fallback. Snapping the
        published child back to its past published_at drops Post.scheduled_at
        into the past, which would make the sibling instantly due.
        """
        from django.db.models.functions import Coalesce

        sibling_account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="bluesky",
            account_platform_id="bs-sibling",
            account_name="Sibling",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        post = Post.objects.create(workspace=self.workspace, caption="multi-platform")
        published_child = PlatformPost.objects.create(
            post=post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            published_at=self.last_week,
            scheduled_at=self.next_week,  # corrupt: dragged into the future
        )
        sibling = PlatformPost.objects.create(
            post=post,
            social_account=sibling_account,
            status=PlatformPost.Status.SCHEDULED,
            scheduled_at=None,  # rides Post.scheduled_at via the Coalesce fallback
        )
        # Parent currently resolves to the (future) corrupt time — the state the
        # queue bug leaves behind (min-of-children with the sibling NULL).
        post.scheduled_at = self.next_week
        post.save(update_fields=["scheduled_at"])

        repair_future_published_scheduled_at(apply=True)

        # Published child snapped back to its real publish instant.
        published_child.refresh_from_db()
        self.assertEqual(published_child.scheduled_at, self.last_week)
        # Parent aggregate did move into the past (the trigger condition)...
        post.refresh_from_db()
        self.assertEqual(post.scheduled_at, self.last_week)
        # ...but the sibling was pinned to its prior effective (future) time, so
        # it is NOT swept up as due by the publisher's Coalesce due-query.
        sibling.refresh_from_db()
        self.assertEqual(sibling.scheduled_at, self.next_week)
        due_ids = set(
            PlatformPost.objects.filter(status=PlatformPost.Status.SCHEDULED)
            .annotate(effective_at=Coalesce("scheduled_at", "post__scheduled_at"))
            .filter(effective_at__lte=timezone.now())
            .values_list("id", flat=True)
        )
        self.assertNotIn(sibling.id, due_ids)


class CalendarChannelSlotViewTests(TestCase):
    """Day/week calendar data should expose channel posting slots."""

    def setUp(self):
        self.factory = RequestFactory()
        self.org = Organization.objects.create(name="Calendar Slots Org", default_timezone="America/New_York")
        self.workspace = Workspace.objects.create(organization=self.org, name="Calendar Slots WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="instagram",
            account_platform_id="ig-calendar-slots",
            account_name="Instagram",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.other_account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_company",
            account_platform_id="li-calendar-slots",
            account_name="LinkedIn",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

    def test_day_view_marks_exact_channel_slot_taken(self):
        target = date(2026, 6, 15)  # Monday
        ny = zoneinfo.ZoneInfo("America/New_York")
        scheduled_at = datetime(2026, 6, 15, 9, 30, tzinfo=ny)
        PostingSlot.objects.create(social_account=self.account, day_of_week=0, time=time(9, 30))
        post = Post.objects.create(workspace=self.workspace, caption="scheduled", scheduled_at=scheduled_at)
        PlatformPost.objects.create(
            post=post,
            social_account=self.account,
            status="scheduled",
            scheduled_at=scheduled_at,
        )

        context = {"display_timezone": "America/New_York"}
        _day_view_data(self.factory.get("/"), self.workspace, target, context)

        cells = {cell["hour"]: cell for cell in context["day_slots"]}
        hour_posts = cells[9]["posts"]
        slot_items = cells[9]["slots"]
        self.assertEqual(slot_items, [])
        self.assertEqual(len(hour_posts), 1)
        self.assertTrue(hour_posts[0].takes_calendar_slot)

    def test_day_view_channel_filter_limits_slot_badges(self):
        target = date(2026, 6, 15)  # Monday
        PostingSlot.objects.create(social_account=self.account, day_of_week=0, time=time(9, 0))
        PostingSlot.objects.create(social_account=self.other_account, day_of_week=0, time=time(9, 0))

        request = self.factory.get("/", {"channel": str(self.account.id)})
        context = {"display_timezone": "America/New_York"}
        _day_view_data(request, self.workspace, target, context)

        cells = {cell["hour"]: cell for cell in context["day_slots"]}
        slot_items = cells[9]["slots"]
        self.assertEqual([slot["account"] for slot in slot_items], [self.account])

    def test_day_view_ignores_malformed_channel_filter(self):
        target = date(2026, 6, 15)  # Monday
        PostingSlot.objects.create(social_account=self.account, day_of_week=0, time=time(9, 0))

        request = self.factory.get("/", {"channel": "not-a-uuid"})
        context = {"display_timezone": "America/New_York"}
        _day_view_data(request, self.workspace, target, context)

        cells = {cell["hour"]: cell for cell in context["day_slots"]}
        slot_items = cells[9]["slots"]
        self.assertEqual([slot["account"] for slot in slot_items], [self.account])

    def test_day_view_includes_workspace_slot_from_adjacent_display_date(self):
        self.workspace.timezone = "America/Los_Angeles"
        self.workspace.save(update_fields=["timezone"])
        target = date(2026, 6, 16)  # Tuesday in Tokyo
        la = zoneinfo.ZoneInfo("America/Los_Angeles")
        scheduled_at = datetime(2026, 6, 15, 9, 0, tzinfo=la)
        PostingSlot.objects.create(social_account=self.account, day_of_week=0, time=time(9, 0))
        post = Post.objects.create(workspace=self.workspace, caption="tokyo-boundary", scheduled_at=scheduled_at)
        PlatformPost.objects.create(
            post=post,
            social_account=self.account,
            status="scheduled",
            scheduled_at=scheduled_at,
        )

        context = {"display_timezone": "Asia/Tokyo"}
        _day_view_data(self.factory.get("/"), self.workspace, target, context)

        cells = {cell["hour"]: cell for cell in context["day_slots"]}
        hour_posts = cells[1]["posts"]
        slot_items = cells[1]["slots"]
        self.assertEqual(slot_items, [])
        self.assertEqual(len(hour_posts), 1)
        self.assertTrue(hour_posts[0].takes_calendar_slot)


class RecurringPostTimezoneTests(TestCase):
    """``generate_recurring_posts`` must preserve the source post's *local*
    wall-clock time across DST boundaries, not drift by the UTC offset.

    The task is not yet wired to run in production, but its time math must be
    correct for when recurrence generation is enabled.
    """

    def test_recurrence_preserves_local_time_across_dst(self):
        org = Organization.objects.create(name="DST Org", default_timezone="America/New_York")
        ws = Workspace.objects.create(organization=org, name="DST WS")
        ny = zoneinfo.ZoneInfo("America/New_York")

        # Source scheduled 09:00 NY on 2026-03-02 (EST, before the 2026-03-08
        # spring-forward). Every weekly recurrence then lands in EDT.
        source = Post.objects.create(
            workspace=ws,
            caption="dst-recurrence",
            scheduled_at=datetime(2026, 3, 2, 9, 0, tzinfo=ny),
        )
        RecurrenceRule.objects.create(
            post=source,
            frequency=RecurrenceRule.Frequency.WEEKLY,
            interval=1,
            end_date=date(2026, 4, 30),
        )

        fixed_now = datetime(2026, 3, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
        with patch("apps.calendar.tasks.timezone.now", return_value=fixed_now):
            generated = generate_recurring_posts()

        self.assertGreater(generated, 0)
        clones = list(Post.objects.filter(workspace=ws, caption="dst-recurrence").exclude(id=source.id))
        self.assertTrue(clones)
        for clone in clones:
            local = clone.scheduled_at.astimezone(ny)
            self.assertEqual(
                (local.hour, local.minute),
                (9, 0),
                msg=f"clone on {local.date()} drifted to {local.time()} (expected 09:00 local)",
            )
        # Confirms at least one recurrence is past the DST transition, so the
        # assertion above actually exercises the boundary.
        self.assertTrue(any(c.scheduled_at.astimezone(ny).date() >= date(2026, 3, 9) for c in clones))

    def test_lookahead_horizon_uses_workspace_local_date(self):
        # The LOOKAHEAD_DAYS horizon must be measured in the workspace's local
        # calendar, not UTC. Otherwise a workspace whose local date differs from
        # the UTC date at run time gets a horizon off by one local day.
        org = Organization.objects.create(name="Horizon Org", default_timezone="Asia/Tokyo")
        ws = Workspace.objects.create(organization=org, name="Horizon WS")
        tokyo = zoneinfo.ZoneInfo("Asia/Tokyo")

        source = Post.objects.create(
            workspace=ws,
            caption="horizon",
            scheduled_at=datetime(2026, 6, 16, 9, 0, tzinfo=tokyo),
        )
        RecurrenceRule.objects.create(
            post=source,
            frequency=RecurrenceRule.Frequency.DAILY,
            interval=1,
        )

        # 2026-06-16 20:00 UTC is already 2026-06-17 in Tokyo (UTC+9), so the
        # workspace-local "today" is one day ahead of the UTC date. Shrink the
        # horizon to keep the generated set tiny.
        fixed_now = datetime(2026, 6, 16, 20, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
        with (
            patch("apps.calendar.tasks.timezone.now", return_value=fixed_now),
            patch("apps.calendar.tasks.LOOKAHEAD_DAYS", 3),
        ):
            generate_recurring_posts()

        clones = Post.objects.filter(workspace=ws, caption="horizon").exclude(id=source.id)
        local_dates = sorted(c.scheduled_at.astimezone(tokyo).date() for c in clones)
        self.assertTrue(local_dates)
        # today_local = 2026-06-17, horizon +3 local days → furthest is 2026-06-20.
        # A UTC-based cutoff (the pre-fix bug) would stop a day short at 06-19.
        self.assertEqual(local_dates[-1], date(2026, 6, 20))


class RecurringPostPlatformExtraTests(TestCase):
    """Recurrence clones must carry each PlatformPost's platform_extra so the
    creator's per-platform settings (e.g. TikTok privacy + interaction flags)
    survive into every generated occurrence rather than reverting to provider
    defaults at publish time.
    """

    def test_recurrence_preserves_platform_extra(self):
        org = Organization.objects.create(name="Extra Org")
        ws = Workspace.objects.create(organization=org, name="Extra WS")
        utc = zoneinfo.ZoneInfo("UTC")
        account = SocialAccount.objects.create(
            workspace=ws,
            platform="tiktok",
            account_platform_id="tt-extra",
            account_name="TikTok",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        source = Post.objects.create(
            workspace=ws,
            caption="extra-recurrence",
            scheduled_at=datetime(2026, 3, 2, 9, 0, tzinfo=utc),
        )
        tiktok_extra = {
            "privacy_level": "SELF_ONLY",
            "disable_comment": False,
            "disable_duet": True,
            "disable_stitch": False,
            "brand_organic_toggle": True,
            "brand_content_toggle": False,
            "is_aigc": False,
        }
        PlatformPost.objects.create(
            post=source,
            social_account=account,
            platform_extra=tiktok_extra,
            scheduled_at=source.scheduled_at,
            status="scheduled",
        )
        RecurrenceRule.objects.create(
            post=source,
            frequency=RecurrenceRule.Frequency.WEEKLY,
            interval=1,
            end_date=date(2026, 4, 30),
        )

        fixed_now = datetime(2026, 3, 1, 12, 0, tzinfo=utc)
        with patch("apps.calendar.tasks.timezone.now", return_value=fixed_now):
            generated = generate_recurring_posts()

        self.assertGreater(generated, 0)
        clones = Post.objects.filter(workspace=ws, caption="extra-recurrence").exclude(id=source.id)
        self.assertTrue(clones.exists())
        for clone in clones:
            clone_pp = clone.platform_posts.get(social_account=account)
            self.assertEqual(clone_pp.platform_extra, tiktok_extra)


class PublishTabTimezoneTests(TestCase):
    """The publish tabs must render times in a user-supplied ?tz= without 500ing."""

    def setUp(self):
        self.user = User.objects.create_user(email="tz@example.com", password="pw", tos_accepted_at=timezone.now())
        self.org = Organization.objects.create(name="Org")
        self.ws = Workspace.objects.create(organization=self.org, name="WS", timezone="Europe/Berlin")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=self.user, workspace=self.ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
        )
        self.sa = SocialAccount.objects.create(
            workspace=self.ws,
            platform="linkedin_personal",
            account_platform_id="li-tz",
            account_name="A",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(
            workspace=self.ws,
            author=self.user,
            caption="x",
            proposed_publish_at=datetime(2027, 9, 1, 9, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Berlin")),
        )
        PlatformPost.objects.create(post=self.post, social_account=self.sa, status="draft")
        self.client.force_login(self.user)

    def test_coerce_timezone_falls_back_on_bad_input(self):
        from apps.calendar.views import _coerce_timezone

        self.assertEqual(_coerce_timezone("Europe/Berlin", None), "Europe/Berlin")
        self.assertEqual(_coerce_timezone("Not/AZone", "Europe/Berlin"), "Europe/Berlin")
        self.assertEqual(_coerce_timezone("", None), "UTC")
        self.assertEqual(_coerce_timezone(None, None), "UTC")
        self.assertEqual(_coerce_timezone("garbage", "also-bad"), "UTC")

    def test_drafts_tab_with_invalid_tz_does_not_500(self):
        url = reverse("calendar:publish_tab_drafts", kwargs={"workspace_id": self.ws.id})
        resp = self.client.get(url + "?tz=Not/AReal/Zone")
        self.assertEqual(resp.status_code, 200)
        # Falls back to the workspace zone, so the proposed badge still renders.
        self.assertContains(resp, "Proposed")

    def test_drafts_tab_with_empty_tz_does_not_500(self):
        url = reverse("calendar:publish_tab_drafts", kwargs={"workspace_id": self.ws.id})
        resp = self.client.get(url + "?tz=")
        self.assertEqual(resp.status_code, 200)


class SlotOccupancyQueueTests(TestCase):
    """Stable slot-occupancy: local ops fill/vacate one slot and preserve gaps."""

    def setUp(self):
        # Freeze now so the candidate list the tests compute via _cands() can't
        # drift from the list the service computes microseconds later (crossing a
        # 09:00 slot boundary would otherwise shift the window by one).
        self._now_patcher = patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 7, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo("UTC")),
        )
        self._now_patcher.start()
        self.addCleanup(self._now_patcher.stop)
        self.org = Organization.objects.create(name="Slot Org", default_timezone="UTC")
        self.workspace = Workspace.objects.create(organization=self.org, name="Slot WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-slot",
            account_name="Slot",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        # One slot every weekday at 09:00 → deterministic, dense candidate list.
        for day in range(7):
            PostingSlot.objects.create(social_account=self.account, day_of_week=day, time=time(9, 0))
        self.queue = Queue.objects.create(workspace=self.workspace, name="Slot Q", social_account=self.account)

    def _cands(self, n=6):
        return _next_slot_datetimes(self.account, timezone.now(), count=n)

    def _occupy(self, slot_dt, *, queued=True, caption="occupied"):
        post = Post.objects.create(workspace=self.workspace, caption=caption)
        pp = PlatformPost.objects.create(
            post=post,
            social_account=self.account,
            status=PlatformPost.Status.SCHEDULED,
            scheduled_at=slot_dt,
        )
        entry = None
        if queued:
            entry = QueueEntry.objects.create(queue=self.queue, post=post, position=0, assigned_slot_datetime=slot_dt)
        return post, pp, entry

    def _add(self, caption="new"):
        post = Post.objects.create(workspace=self.workspace, caption=caption)
        PlatformPost.objects.create(post=post, social_account=self.account, status=PlatformPost.Status.DRAFT)
        return post

    def test_next_available_fills_first_gap(self):
        c = self._cands()
        self._occupy(c[0])  # [0] taken
        self._occupy(c[2])  # [2] taken, [1] is the gap
        post = self._add()

        add_post_next_available(post, self.queue)

        pp = PlatformPost.objects.get(post=post, social_account=self.account)
        self.assertEqual(pp.scheduled_at, c[1])

    def test_next_available_leaves_occupied_entries_unchanged(self):
        c = self._cands()
        _, pp0, _ = self._occupy(c[0])
        _, pp2, _ = self._occupy(c[2])

        add_post_next_available(self._add(), self.queue)

        pp0.refresh_from_db()
        pp2.refresh_from_db()
        self.assertEqual(pp0.scheduled_at, c[0])
        self.assertEqual(pp2.scheduled_at, c[2])

    def test_prioritize_with_slot0_taken_ladders_and_preserves_gap(self):
        c = self._cands()
        _, pp_a, _ = self._occupy(c[0], caption="A")
        _, pp_b, _ = self._occupy(c[2], caption="B")  # gap at [1]
        post = self._add()

        prioritize(post, self.queue)

        pp_new = PlatformPost.objects.get(post=post, social_account=self.account)
        pp_a.refresh_from_db()
        pp_b.refresh_from_db()
        self.assertEqual(pp_new.scheduled_at, c[0])  # new at the top
        self.assertEqual(pp_a.scheduled_at, c[1])  # old[0] → [1]
        self.assertEqual(pp_b.scheduled_at, c[3])  # old[2] → [3] (gap now at [2])

    def test_prioritize_with_slot0_free_moves_nothing(self):
        c = self._cands()
        _, pp_a, _ = self._occupy(c[1], caption="A")  # [0] free
        post = self._add()

        prioritize(post, self.queue)

        pp_new = PlatformPost.objects.get(post=post, social_account=self.account)
        pp_a.refresh_from_db()
        self.assertEqual(pp_new.scheduled_at, c[0])
        self.assertEqual(pp_a.scheduled_at, c[1])  # untouched

    def test_remove_leaves_gap_drafts_child_and_not_due(self):
        c = self._cands()
        post_a, pp_a, entry_a = self._occupy(c[0], caption="A")
        _, pp_b, _ = self._occupy(c[1], caption="B")

        remove_from_queue(entry_a)

        self.assertFalse(QueueEntry.objects.filter(id=entry_a.id).exists())
        pp_a.refresh_from_db()
        post_a.refresh_from_db()
        self.assertEqual(pp_a.status, PlatformPost.Status.DRAFT)
        self.assertIsNone(pp_a.scheduled_at)
        self.assertIsNone(post_a.scheduled_at)
        pp_b.refresh_from_db()
        self.assertEqual(pp_b.scheduled_at, c[1])  # neighbour untouched

        # Drafted child is not swept up by the publisher's due query.
        from django.db.models.functions import Coalesce

        due = set(
            PlatformPost.objects.filter(status=PlatformPost.Status.SCHEDULED)
            .annotate(eff=Coalesce("scheduled_at", "post__scheduled_at"))
            .filter(eff__lte=timezone.now())
            .values_list("id", flat=True)
        )
        self.assertNotIn(pp_a.id, due)

    def test_reslot_moves_entry_to_first_gap(self):
        c = self._cands()
        post_a, pp_a, entry_a = self._occupy(c[2], caption="A")  # [0],[1] free

        reslot_to_next_available(entry_a)

        pp_a.refresh_from_db()
        self.assertEqual(pp_a.scheduled_at, c[0])  # excludes itself → first gap
        # Still a single entry (upsert, not duplicated).
        self.assertEqual(QueueEntry.objects.filter(post=post_a, queue=self.queue).count(), 1)

    def test_add_next_available_upserts_existing_entry(self):
        c = self._cands()
        post_a, pp_a, _ = self._occupy(c[2], caption="A")
        self._occupy(c[0], caption="B")  # [0] taken, [1] free

        add_post_next_available(post_a, self.queue)  # post_a already queued

        pp_a.refresh_from_db()
        self.assertEqual(pp_a.scheduled_at, c[1])  # moved to first gap, excluding self
        self.assertEqual(QueueEntry.objects.filter(post=post_a, queue=self.queue).count(), 1)

    def test_drafting_child_removes_queue_entry(self):
        # Cancel/unschedule parity: transitioning a queued child back to draft
        # drops its QueueEntry (so no orphan with a stale slot lingers).
        from apps.composer.services import transition_platform_post

        c = self._cands()
        post, pp, entry = self._occupy(c[0], caption="A")

        transition_platform_post(pp, "draft")

        pp.refresh_from_db()
        self.assertEqual(pp.status, PlatformPost.Status.DRAFT)
        self.assertIsNone(pp.scheduled_at)
        self.assertFalse(QueueEntry.objects.filter(id=entry.id).exists())

    def test_queue_full_raises_when_channel_has_no_slots(self):
        slotless = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="bluesky",
            account_platform_id="bs-slotless",
            account_name="Slotless",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        queue = Queue.objects.create(workspace=self.workspace, name="Empty Q", social_account=slotless)
        post = Post.objects.create(workspace=self.workspace, caption="x")
        PlatformPost.objects.create(post=post, social_account=slotless, status=PlatformPost.Status.DRAFT)

        with self.assertRaises(QueueFullError):
            add_post_next_available(post, queue)

    def test_prioritize_ladder_skips_foreign_occupied_slot(self):
        # A manually-scheduled post (no QueueEntry) the queue can't move must not
        # be double-booked: the laddered mover skips its slot.
        c = self._cands()
        _, pp_mover, _ = self._occupy(c[0], caption="mover")  # queue entry holds slot 0
        foreign = Post.objects.create(workspace=self.workspace, caption="manual")
        pp_foreign = PlatformPost.objects.create(
            post=foreign, social_account=self.account, status=PlatformPost.Status.SCHEDULED, scheduled_at=c[1]
        )
        post = self._add()

        prioritize(post, self.queue)

        pp_new = PlatformPost.objects.get(post=post, social_account=self.account)
        pp_mover.refresh_from_db()
        pp_foreign.refresh_from_db()
        self.assertEqual(pp_new.scheduled_at, c[0])  # new takes the top
        self.assertEqual(pp_foreign.scheduled_at, c[1])  # immovable, untouched
        self.assertEqual(pp_mover.scheduled_at, c[2])  # skipped the foreign slot
        # Three live posts hold three distinct slots — no collision.
        self.assertEqual(len({pp_new.scheduled_at, pp_mover.scheduled_at, pp_foreign.scheduled_at}), 3)

    def test_prioritize_raises_queue_full_when_ladder_exhausts_horizon(self):
        # A channel with a single weekly slot: fill every slot in the horizon, so
        # the prioritize ladder has nowhere to push the top mover.
        weekly = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="bluesky",
            account_platform_id="bs-weekly",
            account_name="W",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        PostingSlot.objects.create(social_account=weekly, day_of_week=0, time=time(9, 0))  # Mondays only
        queue = Queue.objects.create(workspace=self.workspace, name="Weekly Q", social_account=weekly)
        for i, dt in enumerate(_next_slot_datetimes(weekly, timezone.now(), count=200)):
            p = Post.objects.create(workspace=self.workspace, caption=f"m{i}")
            PlatformPost.objects.create(
                post=p, social_account=weekly, status=PlatformPost.Status.SCHEDULED, scheduled_at=dt
            )
            QueueEntry.objects.create(queue=queue, post=p, position=i, assigned_slot_datetime=dt)

        newp = Post.objects.create(workspace=self.workspace, caption="new")
        PlatformPost.objects.create(post=newp, social_account=weekly, status=PlatformPost.Status.DRAFT)

        with self.assertRaises(QueueFullError):
            prioritize(newp, queue)

    def test_prioritize_keys_on_scheduled_at_not_stale_assigned(self):
        # A queued post dragged on the calendar (reschedule_post) moves
        # pp.scheduled_at but leaves QueueEntry.assigned_slot_datetime stale.
        # prioritize must read the real (scheduled_at) slot, not the stale one.
        c = self._cands()
        post_a, pp_a, _ = self._occupy(c[0], caption="A")  # entry assigned=c[0]
        pp_a.scheduled_at = c[2]  # "dragged" to c[2]; assigned stays c[0]
        pp_a.save(update_fields=["scheduled_at"])

        prioritize(self._add(caption="B"), self.queue)

        pp_b = PlatformPost.objects.get(post__caption="B", social_account=self.account)
        pp_a.refresh_from_db()
        # Slot 0 is really free (A is at c[2]); B takes it and A is untouched —
        # no mis-ladder off the stale assigned_slot_datetime.
        self.assertEqual(pp_b.scheduled_at, c[0])
        self.assertEqual(pp_a.scheduled_at, c[2])

    def test_reorder_keys_on_scheduled_at_not_stale_assigned(self):
        c = self._cands()
        post1, pp1, e1 = self._occupy(c[0], caption="one")
        post2, pp2, e2 = self._occupy(c[1], caption="two")
        pp1.scheduled_at = c[2]  # drag post1 to c[2]; e1.assigned stays c[0]
        pp1.save(update_fields=["scheduled_at"])

        reorder_queue(self.queue, [str(e1.id), str(e2.id)])

        pp1.refresh_from_db()
        pp2.refresh_from_db()
        # Real occupied instants are {c[1], c[2]} (not the stale {c[0], c[1]});
        # redistributed in order → e1=c[1], e2=c[2]. No double-book.
        self.assertEqual(pp1.scheduled_at, c[1])
        self.assertEqual(pp2.scheduled_at, c[2])
        self.assertEqual(len({pp1.scheduled_at, pp2.scheduled_at}), 2)

    def test_reslot_is_noop_for_publishing_post(self):
        # A protected (publishing) post's schedule is history — reslot must not
        # overwrite it with a future slot (the corruption class repair exists for).
        c = self._cands()
        post = Post.objects.create(workspace=self.workspace, caption="pub")
        pp = PlatformPost.objects.create(
            post=post, social_account=self.account, status=PlatformPost.Status.PUBLISHING, scheduled_at=c[2]
        )
        entry = QueueEntry.objects.create(queue=self.queue, post=post, position=0, assigned_slot_datetime=c[2])

        reslot_to_next_available(entry)

        pp.refresh_from_db()
        self.assertEqual(pp.scheduled_at, c[2])  # untouched

    def test_remove_clears_schedule_for_failed_child(self):
        c = self._cands()
        post = Post.objects.create(workspace=self.workspace, caption="failed")
        pp = PlatformPost.objects.create(
            post=post, social_account=self.account, status=PlatformPost.Status.FAILED, scheduled_at=c[0]
        )
        entry = QueueEntry.objects.create(queue=self.queue, post=post, position=0, assigned_slot_datetime=c[0])

        remove_from_queue(entry)

        self.assertFalse(QueueEntry.objects.filter(id=entry.id).exists())
        pp.refresh_from_db()
        self.assertEqual(pp.status, PlatformPost.Status.DRAFT)
        self.assertIsNone(pp.scheduled_at)  # no longer lingers on the calendar


class QueueEntryEndpointTests(TestCase):
    """HTTP endpoints for single-entry remove / reslot (workspace-scoped)."""

    def setUp(self):
        self.user = User.objects.create_user(email="qe@example.com", password="pw", tos_accepted_at=timezone.now())
        self.org = Organization.objects.create(name="EP Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="EP WS")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=self.user, workspace=self.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-ep",
            account_name="EP",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        for day in range(7):
            PostingSlot.objects.create(social_account=self.account, day_of_week=day, time=time(9, 0))
        self.queue = Queue.objects.create(workspace=self.workspace, name="EP Q", social_account=self.account)
        self.client.force_login(self.user)

    def _queue_post(self, slot_dt):
        post = Post.objects.create(workspace=self.workspace, caption="x")
        PlatformPost.objects.create(
            post=post, social_account=self.account, status=PlatformPost.Status.SCHEDULED, scheduled_at=slot_dt
        )
        entry = QueueEntry.objects.create(queue=self.queue, post=post, position=0, assigned_slot_datetime=slot_dt)
        return post, entry

    def _remove_url(self, entry_id, queue_id=None):
        return reverse(
            "calendar:queue_entry_remove",
            kwargs={"workspace_id": self.workspace.id, "queue_id": queue_id or self.queue.id, "entry_id": entry_id},
        )

    def test_remove_entry_deletes_and_drafts(self):
        c = _next_slot_datetimes(self.account, timezone.now(), count=2)
        post, entry = self._queue_post(c[0])
        resp = self.client.post(self._remove_url(entry.id), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 204)
        self.assertIn("queueReordered", resp.headers.get("HX-Trigger", ""))
        self.assertFalse(QueueEntry.objects.filter(id=entry.id).exists())
        pp = PlatformPost.objects.get(post=post)
        self.assertEqual(pp.status, PlatformPost.Status.DRAFT)
        self.assertIsNone(pp.scheduled_at)

    def test_remove_idempotent_when_already_gone(self):
        import uuid as _uuid

        resp = self.client.post(self._remove_url(_uuid.uuid4()), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 204)

    def test_remove_foreign_workspace_entry_is_noop(self):
        other_org = Organization.objects.create(name="Other")
        other_ws = Workspace.objects.create(organization=other_org, name="Other WS")
        other_acct = SocialAccount.objects.create(
            workspace=other_ws,
            platform="linkedin_personal",
            account_platform_id="li-other",
            account_name="O",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        other_queue = Queue.objects.create(workspace=other_ws, name="OQ", social_account=other_acct)
        other_post = Post.objects.create(workspace=other_ws, caption="o")
        other_entry = QueueEntry.objects.create(queue=other_queue, post=other_post, position=0)

        # Member of self.workspace targets their own workspace_id but a foreign entry.
        resp = self.client.post(self._remove_url(other_entry.id, queue_id=other_queue.id), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 204)
        self.assertTrue(QueueEntry.objects.filter(id=other_entry.id).exists())

    def test_reslot_moves_to_next_gap(self):
        c = _next_slot_datetimes(self.account, timezone.now(), count=3)
        post, entry = self._queue_post(c[2])  # [0],[1] free
        url = reverse(
            "calendar:queue_entry_reslot",
            kwargs={"workspace_id": self.workspace.id, "queue_id": self.queue.id, "entry_id": entry.id},
        )
        resp = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 204)
        pp = PlatformPost.objects.get(post=post)
        self.assertEqual(pp.scheduled_at, c[0])

    def test_queue_detail_page_renders_chronologically(self):
        # Smoke: the detail page renders with the new remove button and orders
        # entries by slot datetime (an earlier slot added second still shows first).
        c = _next_slot_datetimes(self.account, timezone.now(), count=2)
        later = Post.objects.create(workspace=self.workspace, caption="LATER caption")
        PlatformPost.objects.create(
            post=later, social_account=self.account, status=PlatformPost.Status.SCHEDULED, scheduled_at=c[1]
        )
        QueueEntry.objects.create(queue=self.queue, post=later, position=0, assigned_slot_datetime=c[1])
        earlier = Post.objects.create(workspace=self.workspace, caption="EARLIER caption")
        PlatformPost.objects.create(
            post=earlier, social_account=self.account, status=PlatformPost.Status.SCHEDULED, scheduled_at=c[0]
        )
        QueueEntry.objects.create(queue=self.queue, post=earlier, position=1, assigned_slot_datetime=c[0])

        url = reverse("calendar:queue_detail", kwargs={"workspace_id": self.workspace.id, "queue_id": self.queue.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Remove from queue")
        body = resp.content.decode()
        self.assertLess(body.index("EARLIER caption"), body.index("LATER caption"))
