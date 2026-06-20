"""Tests for the Content Calendar app (T-1A.2)."""

import zoneinfo
from datetime import date, datetime, time
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import PostingSlot, Queue, QueueEntry, RecurrenceRule
from apps.calendar.services import add_to_queue
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

        hour_posts = dict((hour, posts) for hour, posts, _slots in context["day_slots"])[9]
        slot_items = dict((hour, slots) for hour, _posts, slots in context["day_slots"])[9]
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

        slot_items = dict((hour, slots) for hour, _posts, slots in context["day_slots"])[9]
        self.assertEqual([slot["account"] for slot in slot_items], [self.account])


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
