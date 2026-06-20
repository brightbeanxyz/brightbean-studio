"""Proposed publishing datetime — service + composer-view behaviour.

A draft can carry an optional ``proposed_publish_at`` suggestion, entered via
the Schedule Post panel. Saving a draft captures it; scheduling clears it; and
a post that is already scheduled must never have the panel reinterpreted as a
proposal.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post
from apps.composer.services import create_post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

BERLIN = ZoneInfo("Europe/Berlin")
# 2027-09-01 is CEST (UTC+2), so 09:00 local == 07:00 UTC — an unambiguous instant.
PROPOSED_LOCAL = datetime(2027, 9, 1, 9, 0, tzinfo=BERLIN)


def _make_workspace():
    org = Organization.objects.create(name="Org")
    ws = Workspace.objects.create(organization=org, name="WS", timezone="Europe/Berlin")
    sa = SocialAccount.objects.create(
        workspace=ws,
        platform="linkedin_personal",
        account_platform_id="li-1",
        account_name="Acct",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    return org, ws, sa


class ProposedPublishAtServiceTests(TestCase):
    """create_post stores the optional proposal independent of status."""

    def setUp(self):
        self.org, self.ws, self.sa = _make_workspace()

    def test_create_post_stores_proposed(self):
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="hi",
            status="draft",
            proposed_publish_at=PROPOSED_LOCAL,
        )
        # Re-fetch so this proves persistence, not just the in-memory attribute
        # (a missing migration/column would otherwise pass silently).
        post = Post.objects.get(pk=post.pk)
        self.assertEqual(post.proposed_publish_at, PROPOSED_LOCAL)

    def test_create_post_defaults_to_none(self):
        post = create_post(workspace=self.ws, social_account=self.sa, caption="hi", status="draft")
        self.assertIsNone(post.proposed_publish_at)

    def test_scheduling_clears_proposed(self):
        # create_post(status='scheduled') routes through sync_post_scheduled_at,
        # which now drops any proposal centrally — the two never coexist.
        when = timezone.now() + timedelta(days=10)
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="hi",
            status="scheduled",
            scheduled_at=when,
            proposed_publish_at=PROPOSED_LOCAL,
        )
        post = Post.objects.get(pk=post.pk)
        self.assertIsNotNone(post.scheduled_at)
        self.assertIsNone(post.proposed_publish_at)


class ProposedPublishAtSaveTests(TestCase):
    """POST /workspace/<id>/composer/compose/save/ proposed-time handling."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org, self.ws, self.sa = _make_workspace()
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=self.user, workspace=self.ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
        )
        self.client.force_login(self.user)
        self.save_url = reverse("composer:save_post", kwargs={"workspace_id": self.ws.id})

    def _edit_save_url(self, post_id):
        return reverse("composer:save_post_edit", kwargs={"workspace_id": self.ws.id, "post_id": post_id})

    def _latest(self):
        return Post.objects.filter(workspace=self.ws).order_by("-created_at").first()

    def test_save_draft_captures_proposed_in_workspace_tz(self):
        resp = self.client.post(
            self.save_url,
            data={
                "action": "save_draft",
                "title": "t",
                "caption": "body",
                "tags": "",
                "selected_accounts": str(self.sa.id),
                "scheduled_date": "2027-09-01",
                "scheduled_time": "09:00",
            },
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        post = self._latest()
        self.assertEqual(post.proposed_publish_at, PROPOSED_LOCAL)
        # A proposal is NOT a schedule — the publisher column stays empty.
        self.assertIsNone(post.scheduled_at)

    def test_save_draft_blank_clears_proposed(self):
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="body",
            status="draft",
            proposed_publish_at=PROPOSED_LOCAL,
            author=self.user,
        )
        resp = self.client.post(
            self._edit_save_url(post.id),
            data={
                "action": "save_draft",
                "caption": "body",
                "tags": "",
                "selected_accounts": str(self.sa.id),
                "scheduled_date": "",
                "scheduled_time": "",
            },
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        post.refresh_from_db()
        self.assertIsNone(post.proposed_publish_at)

    def test_schedule_clears_proposed_and_sets_scheduled(self):
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="body",
            status="draft",
            proposed_publish_at=PROPOSED_LOCAL,
            author=self.user,
        )
        resp = self.client.post(
            self._edit_save_url(post.id),
            data={
                "action": "schedule",
                "caption": "body",
                "tags": "",
                "selected_accounts": str(self.sa.id),
                "scheduled_date": "2027-09-01",
                "scheduled_time": "09:00",
            },
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        post.refresh_from_db()
        self.assertIsNone(post.proposed_publish_at)
        self.assertIsNotNone(post.scheduled_at)
        self.assertTrue(post.platform_posts.filter(status="scheduled").exists())

    def test_save_draft_on_scheduled_post_leaves_schedule_untouched(self):
        when = timezone.now().astimezone(BERLIN).replace(microsecond=0) + timedelta(days=30)
        post = Post.objects.create(workspace=self.ws, author=self.user, caption="x", scheduled_at=when)
        PlatformPost.objects.create(post=post, social_account=self.sa, status="scheduled", scheduled_at=when)
        resp = self.client.post(
            self._edit_save_url(post.id),
            data={
                "action": "save_draft",
                "caption": "x",
                "tags": "",
                "selected_accounts": str(self.sa.id),
                "scheduled_date": "2027-09-01",
                "scheduled_time": "09:00",
            },
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        post.refresh_from_db()
        # Already-scheduled → the panel is the live schedule, not a proposal.
        self.assertIsNone(post.proposed_publish_at)
        self.assertEqual(post.scheduled_at, when)
        self.assertTrue(post.platform_posts.filter(status="scheduled").exists())

    def test_edit_prefills_proposed_and_sets_flag(self):
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="x",
            status="draft",
            proposed_publish_at=PROPOSED_LOCAL,
            author=self.user,
        )
        resp = self.client.get(
            reverse("composer:compose_edit", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["schedule_prefill_is_proposed"])
        self.assertFalse(resp.context["post_is_scheduled"])
        body = resp.content.decode("utf-8")
        self.assertIn('value="2027-09-01"', body)
        self.assertIn("prefillIsProposed = true", body)

    def test_drafts_list_renders_proposed_badge(self):
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="x",
            status="draft",
            proposed_publish_at=PROPOSED_LOCAL,
            author=self.user,
        )
        self.assertEqual(post.platform_posts.get().status, "draft")
        resp = self.client.get(reverse("composer:drafts_list", kwargs={"workspace_id": self.ws.id}))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        # The proposed-time badge renders with its distinguishing title + accent
        # and the "Proposed Publishing <datetime>" copy.
        self.assertIn('title="Proposed publishing time"', body)
        self.assertIn("Proposed Publishing", body)
        # Rendered in the workspace timezone (Europe/Berlin, UTC+2 on this date),
        # not server/UTC time.
        self.assertIn("Sep 1, 9:00", body)
        self.assertNotIn("Sep 1, 7:00", body)

    def test_submit_for_approval_with_blank_panel_preserves_proposed(self):
        # A proposal set via the API must survive being routed through approval
        # even when the submit POST carries no schedule-panel values.
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="body",
            status="draft",
            proposed_publish_at=PROPOSED_LOCAL,
            author=self.user,
        )
        resp = self.client.post(
            self._edit_save_url(post.id),
            data={
                "action": "submit_for_approval",
                "caption": "body",
                "tags": "",
                "selected_accounts": str(self.sa.id),
                "scheduled_date": "",
                "scheduled_time": "",
            },
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        post.refresh_from_db()
        self.assertEqual(post.proposed_publish_at, PROPOSED_LOCAL)
        self.assertTrue(post.platform_posts.filter(status="pending_review").exists())

    def test_chip_transition_to_scheduled_clears_proposed(self):
        # The per-account chip endpoint bypasses the service layer; it must
        # still drop the proposal when it commits a child to publishing.
        post = create_post(
            workspace=self.ws,
            social_account=self.sa,
            caption="body",
            status="draft",
            proposed_publish_at=PROPOSED_LOCAL,
            author=self.user,
        )
        pp = post.platform_posts.get()
        url = reverse(
            "composer:transition_platform_post",
            kwargs={"workspace_id": self.ws.id, "post_id": post.id, "platform_post_id": pp.id},
        )
        resp = self.client.post(url, data={"target_status": "scheduled"})
        self.assertEqual(resp.status_code, 200)
        post.refresh_from_db()
        self.assertIsNone(post.proposed_publish_at)
        # The clear must not disturb the scheduling aggregate the publisher reads.
        self.assertIsNone(post.scheduled_at)
        pp.refresh_from_db()
        self.assertEqual(pp.status, "scheduled")

    def test_publisher_fallback_still_picks_up_scheduled_post(self):
        # Regression guard for the publish path: a scheduled child with NULL
        # scheduled_at must stay "due" via the Post.scheduled_at Coalesce
        # fallback. The proposal handling must never disturb that aggregate,
        # else such a post would silently never publish.
        from apps.publisher.engine import PublishEngine

        past = timezone.now() - timedelta(minutes=5)
        post = Post.objects.create(workspace=self.ws, author=self.user, caption="x", scheduled_at=past)
        pp = PlatformPost.objects.create(post=post, social_account=self.sa, status="scheduled", scheduled_at=None)
        due_ids = {d.id for d in PublishEngine()._get_due_platform_posts()}
        self.assertIn(pp.id, due_ids)
