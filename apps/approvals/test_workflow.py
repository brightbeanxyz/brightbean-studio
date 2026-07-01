"""Workflow tests for the redesigned approval surface.

Covers the unified action contract (204 + HX-Trigger toast/refresh), the no-op
"Nothing to update" path, bulk-reject comment enforcement, and the on_hold
(client hold) transitions including its exclusion from the publish path.
"""

import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals import services
from apps.approvals.models import ApprovalAction
from apps.composer.models import PlatformPost, Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


def _make_user(email):
    user = User.objects.create_user(email=email, password="testpass123", tos_accepted_at=timezone.now())
    auto_org_ids = list(OrgMembership.objects.filter(user=user).values_list("organization_id", flat=True))
    WorkspaceMembership.objects.filter(user=user).delete()
    OrgMembership.objects.filter(user=user).delete()
    Organization.objects.filter(id__in=auto_org_ids).delete()
    return user


class ApprovalWorkflowBase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.ws = Workspace.objects.create(organization=self.org, name="WS")
        self.reviewer = _make_user("reviewer@example.com")
        self.author = _make_user("author@example.com")
        OrgMembership.objects.create(user=self.reviewer, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.reviewer, workspace=self.ws, workspace_role="manager")
        WorkspaceMembership.objects.create(user=self.author, workspace=self.ws, workspace_role="contributor")
        self.account = SocialAccount.objects.create(
            workspace=self.ws,
            platform="linkedin_personal",
            account_platform_id="li-1",
            account_name="LI",
            connection_status="connected",
        )

    def _post(self, status):
        post = Post.objects.create(workspace=self.ws, author=self.author, caption="Original caption")
        PlatformPost.objects.create(post=post, social_account=self.account, status=status)
        return post

    def _triggers(self, response):
        return json.loads(response.headers["HX-Trigger"])


class ActionViewContractTests(ApprovalWorkflowBase):
    def test_approve_returns_toast_and_refresh(self):
        post = self._post("pending_review")
        self.client.force_login(self.reviewer)
        url = reverse("approvals:approve", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 204)
        trig = self._triggers(resp)
        self.assertIn("showToast", trig)
        self.assertIn("approvalAction", trig)
        self.assertEqual(post.platform_posts.get().status, "approved")

    def test_approve_noop_warns_without_refresh(self):
        post = self._post("approved")  # nothing to do
        self.client.force_login(self.reviewer)
        url = reverse("approvals:approve", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 204)
        trig = self._triggers(resp)
        self.assertEqual(trig["showToast"]["tone"], "warn")
        self.assertNotIn("approvalAction", trig)

    def test_request_changes_requires_comment(self):
        post = self._post("pending_review")
        self.client.force_login(self.reviewer)
        url = reverse("approvals:request_changes", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        resp = self.client.post(url, data={"comment": ""})
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(self._triggers(resp)["showToast"]["tone"], "error")
        self.assertEqual(post.platform_posts.get().status, "pending_review")

    def test_request_changes_with_comment(self):
        post = self._post("pending_review")
        self.client.force_login(self.reviewer)
        url = reverse("approvals:request_changes", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        resp = self.client.post(url, data={"comment": "Tighten the hook"})
        self.assertEqual(resp.status_code, 204)
        self.assertIn("approvalAction", self._triggers(resp))
        self.assertEqual(post.platform_posts.get().status, "changes_requested")
        self.assertTrue(ApprovalAction.objects.filter(post=post, action="changes_requested").exists())

    def test_bulk_reject_requires_comment(self):
        post = self._post("pending_review")
        self.client.force_login(self.reviewer)
        url = reverse("approvals:bulk_action", kwargs={"workspace_id": self.ws.id})
        resp = self.client.post(url, data={"action": "reject", "post_ids": [str(post.id)]})
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(self._triggers(resp)["showToast"]["tone"], "error")
        self.assertEqual(post.platform_posts.get().status, "pending_review")

    def test_bulk_approve(self):
        p1, p2 = self._post("pending_review"), self._post("pending_review")
        self.client.force_login(self.reviewer)
        url = reverse("approvals:bulk_action", kwargs={"workspace_id": self.ws.id})
        resp = self.client.post(url, data={"action": "approve", "post_ids": [str(p1.id), str(p2.id)]})
        self.assertEqual(resp.status_code, 204)
        self.assertIn("bulkActionComplete", self._triggers(resp))
        self.assertEqual(p1.platform_posts.get().status, "approved")
        self.assertEqual(p2.platform_posts.get().status, "approved")


class HoldTests(ApprovalWorkflowBase):
    def test_request_hold_then_resume(self):
        post = self._post("approved")
        services.request_hold(post, self.author, self.ws, "Legal wants to check the figures")
        self.assertEqual(post.platform_posts.get().status, "on_hold")
        self.assertTrue(ApprovalAction.objects.filter(post=post, action="held").exists())

        services.resume_hold(post, self.reviewer, self.ws)
        self.assertEqual(post.platform_posts.get().status, "approved")

    def test_request_hold_requires_comment(self):
        post = self._post("approved")
        with self.assertRaises(ValueError):
            services.request_hold(post, self.author, self.ws, "   ")
        self.assertEqual(post.platform_posts.get().status, "approved")

    def test_on_hold_is_not_publishable(self):
        pp = self._post("on_hold").platform_posts.get()
        # No on_hold → scheduled / publishing edge: a held post can't slip into the
        # publisher, which only pulls scheduled rows.
        self.assertFalse(pp.can_transition_to("scheduled"))
        self.assertFalse(pp.can_transition_to("publishing"))

    def test_hold_notification_defaults_to_email(self):
        from apps.notifications.engine import _resolve_channels
        from apps.notifications.models import Channel, EventType

        # A reviewer with no explicit preferences must still get the client-hold
        # notice by email (the event needs a DEFAULT_CHANNELS entry).
        channels = _resolve_channels(self.reviewer, EventType.APPROVAL_HOLD_REQUESTED)
        self.assertIn(Channel.EMAIL, channels)
        self.assertIn(Channel.IN_APP, channels)


class TwoStageFlowTests(ApprovalWorkflowBase):
    def test_submit_approve_client_hold_path(self):
        self.ws.approval_workflow_mode = "required_internal_and_client"
        self.ws.save(update_fields=["approval_workflow_mode"])
        post = self._post("draft")

        services.submit_for_review(post, self.author, self.ws)
        self.assertEqual(post.platform_posts.get().status, "pending_review")

        services.approve_post(post, self.reviewer, self.ws)  # internal → client stage
        self.assertEqual(post.platform_posts.get().status, "pending_client")

        services.approve_post(post, self.author, self.ws)  # client sign-off
        self.assertEqual(post.platform_posts.get().status, "approved")

        services.request_hold(post, self.author, self.ws, "Hold for a sec")
        self.assertEqual(post.platform_posts.get().status, "on_hold")

    def test_two_stage_defers_approved_notification_to_client_signoff(self):
        from apps.notifications.models import EventType, Notification

        self.ws.approval_workflow_mode = "required_internal_and_client"
        self.ws.save(update_fields=["approval_workflow_mode"])
        post = self._post("pending_review")

        # Internal approval only advances to pending_client — the author must NOT
        # be told "approved" yet.
        services.approve_post(post, self.reviewer, self.ws)
        self.assertEqual(post.platform_posts.get().status, "pending_client")
        self.assertFalse(Notification.objects.filter(user=self.author, event_type=EventType.POST_APPROVED).exists())

        # Client sign-off reaches approved — now the author is notified.
        services.approve_post(post, self.reviewer, self.ws)
        self.assertEqual(post.platform_posts.get().status, "approved")
        self.assertTrue(Notification.objects.filter(user=self.author, event_type=EventType.POST_APPROVED).exists())


class DerivedStatusTests(TestCase):
    def test_held_child_surfaces_at_post_level(self):
        from apps.composer.status import derive_post_status

        # A client-held platform must surface at the Post level rather than being
        # masked by an un-held sibling — otherwise the per-post approvals row shows
        # the wrong badge and the Resume action (gated on post.status=='on_hold') vanishes.
        self.assertEqual(derive_post_status(["on_hold"]), "on_hold")
        self.assertEqual(derive_post_status(["on_hold", "approved"]), "on_hold")
        self.assertEqual(derive_post_status(["on_hold", "scheduled"]), "on_hold")

    def test_on_hold_does_not_mask_published(self):
        from apps.composer.status import derive_post_status

        # A channel that has already published must not be hidden behind a held
        # sibling — surface the partial outcome instead of "on_hold".
        self.assertEqual(derive_post_status(["published", "on_hold"]), "partially_published")
        self.assertEqual(derive_post_status(["published", "failed", "on_hold"]), "partially_published")


class HoldPublishGuardTests(ApprovalWorkflowBase):
    """A held post must never publish any platform, even a scheduled sibling."""

    def _scheduled_post(self, *, held_sibling):
        from datetime import timedelta

        due = timezone.now() - timedelta(minutes=5)
        post = Post.objects.create(workspace=self.ws, author=self.author, caption="x", scheduled_at=due)
        sched = PlatformPost.objects.create(
            post=post, social_account=self.account, status="scheduled", scheduled_at=due
        )
        if held_sibling:
            acct2 = SocialAccount.objects.create(
                workspace=self.ws,
                platform="instagram_business",
                account_platform_id="ig-2",
                account_name="IG2",
                connection_status="connected",
            )
            PlatformPost.objects.create(post=post, social_account=acct2, status="on_hold")
        return sched

    def test_publisher_skips_post_with_held_sibling(self):
        from apps.publisher.engine import PublishEngine

        sched = self._scheduled_post(held_sibling=True)
        due_ids = [pp.id for pp in PublishEngine()._get_due_platform_posts()]
        self.assertNotIn(sched.id, due_ids)

    def test_publisher_publishes_scheduled_without_hold(self):
        from apps.publisher.engine import PublishEngine

        sched = self._scheduled_post(held_sibling=False)
        due_ids = [pp.id for pp in PublishEngine()._get_due_platform_posts()]
        self.assertIn(sched.id, due_ids)

    def test_publish_group_skips_scheduled_when_sibling_held(self):
        from apps.publisher.engine import PublishEngine

        # Even if a due scheduled row reaches _publish_post_group, the under-lock
        # on_hold re-check must keep it from moving to publishing.
        sched = self._scheduled_post(held_sibling=True)
        PublishEngine()._publish_post_group(sched.post, [sched])
        sched.refresh_from_db()
        self.assertEqual(sched.status, "scheduled")

    def test_retry_path_skips_post_with_held_sibling(self):
        from datetime import timedelta

        from apps.publisher.engine import PublishEngine

        # A retrying scheduled child (retry_count>0) shares status=SCHEDULED with
        # the primary path; the hold guard must cover it too so a held post's
        # retrying sibling doesn't publish.
        post = Post.objects.create(workspace=self.ws, author=self.author, caption="x")
        retry_pp = PlatformPost.objects.create(
            post=post,
            social_account=self.account,
            status="scheduled",
            retry_count=1,
            next_retry_at=timezone.now() - timedelta(minutes=1),
        )
        acct2 = SocialAccount.objects.create(
            workspace=self.ws,
            platform="instagram_business",
            account_platform_id="ig-r",
            account_name="IGr",
            connection_status="connected",
        )
        PlatformPost.objects.create(post=post, social_account=acct2, status="on_hold")

        PublishEngine()._process_retries()
        retry_pp.refresh_from_db()
        self.assertEqual(retry_pp.status, "scheduled")


class ApprovedEditReReviewTests(ApprovalWorkflowBase):
    """Editing an approved post must send it back for re-approval (Option A)."""

    def setUp(self):
        super().setUp()
        self.post = self._post("approved")
        self.client.force_login(self.author)
        self.save_url = reverse("composer:save_post_edit", kwargs={"workspace_id": self.ws.id, "post_id": self.post.id})

    def _payload(self, **overrides):
        data = {
            "action": "save_draft",
            "title": "",
            "caption": self.post.caption,
            "tags": "",
            "selected_accounts": str(self.account.id),
        }
        data.update(overrides)
        return data

    def test_resubmit_service_accepts_approved(self):
        services.resubmit_post(self.post, self.author, self.ws)
        self.assertEqual(self.post.platform_posts.get().status, "pending_review")

    def test_editing_approved_post_reverts_to_pending_review(self):
        resp = self.client.post(self.save_url, data=self._payload(caption="A meaningfully edited caption"))
        self.assertIn(resp.status_code, (200, 204, 302))
        self.assertEqual(self.post.platform_posts.get().status, "pending_review")

    def test_unchanged_save_keeps_approved(self):
        resp = self.client.post(self.save_url, data=self._payload())
        self.assertIn(resp.status_code, (200, 204, 302))
        self.assertEqual(self.post.platform_posts.get().status, "approved")

    def test_scheduling_edited_approved_post_does_not_publish(self):
        # Finding 1: a schedule action in the SAME save as a content edit must not
        # push the edited (no-longer-approved) content straight to scheduled — it
        # goes back for re-review instead.
        from datetime import timedelta

        when = timezone.now() + timedelta(days=1)
        resp = self.client.post(
            self.save_url,
            data=self._payload(
                action="schedule",
                caption="Edited and scheduled in one save",
                scheduled_date=when.strftime("%Y-%m-%d"),
                scheduled_time=when.strftime("%H:%M"),
            ),
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        self.assertEqual(self.post.platform_posts.get().status, "pending_review")

    def test_scheduling_unchanged_approved_post_still_schedules(self):
        # Happy path preserved: scheduling an approved post whose content is
        # unchanged proceeds straight to scheduled.
        from datetime import timedelta

        when = timezone.now() + timedelta(days=1)
        resp = self.client.post(
            self.save_url,
            data=self._payload(
                action="schedule",
                scheduled_date=when.strftime("%Y-%m-%d"),
                scheduled_time=when.strftime("%H:%M"),
            ),
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        self.assertEqual(self.post.platform_posts.get().status, "scheduled")

    def test_autosave_edit_reverts_approved(self):
        url = reverse("composer:autosave_edit", kwargs={"workspace_id": self.ws.id, "post_id": self.post.id})
        resp = self.client.post(
            url, data={"title": "", "caption": "Autosaved different text", "selected_accounts": str(self.account.id)}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.post.platform_posts.get().status, "pending_review")

    def _image_asset(self):
        from django.core.files.base import ContentFile

        from apps.media_library.models import MediaAsset

        return MediaAsset.objects.create(
            organization=self.org,
            workspace=self.ws,
            file=ContentFile(b"x", name="pic.png"),
            filename="pic.png",
            media_type=MediaAsset.MediaType.IMAGE,
        )

    def test_attaching_media_reverts_approved(self):
        asset = self._image_asset()
        url = reverse("composer:attach_media", kwargs={"workspace_id": self.ws.id, "post_id": self.post.id})
        resp = self.client.post(url, data={"media_asset_id": str(asset.id)})
        self.assertIn(resp.status_code, (200, 204))
        self.assertEqual(self.post.platform_posts.get().status, "pending_review")

    def test_removing_media_reverts_approved(self):
        from apps.composer.models import PostMedia

        pm = PostMedia.objects.create(post=self.post, media_asset=self._image_asset(), position=0)
        url = reverse(
            "composer:remove_media",
            kwargs={"workspace_id": self.ws.id, "post_id": self.post.id, "media_id": pm.id},
        )
        resp = self.client.post(url)
        self.assertIn(resp.status_code, (200, 204))
        self.assertEqual(self.post.platform_posts.get().status, "pending_review")


class ApprovalTabChannelFilterTests(ApprovalWorkflowBase):
    """The approvals tab's channel + status filters must match the SAME child row.

    A post with an Instagram child pending review and a LinkedIn child in draft
    must NOT surface (or be bulk-actionable) under a LinkedIn + pending_review
    filter — otherwise actions target a channel that isn't actually pending.
    """

    def setUp(self):
        super().setUp()
        self.other = SocialAccount.objects.create(
            workspace=self.ws,
            platform="instagram_business",
            account_platform_id="ig-1",
            account_name="IG",
            connection_status="connected",
        )
        self.post = Post.objects.create(workspace=self.ws, author=self.author, title="MIXEDROW", caption="c")
        PlatformPost.objects.create(post=self.post, social_account=self.other, status="pending_review")  # IG pending
        PlatformPost.objects.create(post=self.post, social_account=self.account, status="draft")  # LinkedIn draft
        self.client.force_login(self.reviewer)
        self.url = reverse("calendar:publish_tab_approvals", kwargs={"workspace_id": self.ws.id})

    def test_channel_filter_hides_row_pending_on_other_channel(self):
        resp = self.client.get(self.url, {"approval_status": "pending_review", "channel": str(self.account.id)})
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "MIXEDROW")

    def test_channel_filter_surfaces_row_pending_on_that_channel(self):
        resp = self.client.get(self.url, {"approval_status": "pending_review", "channel": str(self.other.id)})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "MIXEDROW")


class PortalMixedPostActionTests(TestCase):
    """A pending_client child must expose client actions even when a lower-ranked
    sibling makes the derived Post.status something else (finding 3)."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.ws = Workspace.objects.create(organization=self.org, name="WS")
        self.client_user = _make_user("client@example.com")
        WorkspaceMembership.objects.create(user=self.client_user, workspace=self.ws, workspace_role="client")
        self.author = _make_user("author2@example.com")
        WorkspaceMembership.objects.create(user=self.author, workspace=self.ws, workspace_role="contributor")
        self.ig = SocialAccount.objects.create(
            workspace=self.ws,
            platform="instagram_business",
            account_platform_id="ig-1",
            account_name="IG",
            connection_status="connected",
        )
        self.li = SocialAccount.objects.create(
            workspace=self.ws,
            platform="linkedin_personal",
            account_platform_id="li-1",
            account_name="LI",
            connection_status="connected",
        )

    def _login_portal(self):
        self.client.force_login(self.client_user)
        session = self.client.session
        session["is_portal_session"] = True
        session["portal_workspace_id"] = str(self.ws.id)
        session.save()

    def test_mixed_pending_post_exposes_client_actions(self):
        post = Post.objects.create(workspace=self.ws, author=self.author, title="MIXEDCLIENT", caption="c")
        PlatformPost.objects.create(post=post, social_account=self.ig, status="pending_client")
        PlatformPost.objects.create(post=post, social_account=self.li, status="draft")  # lower-ranked sibling
        # Derived status is the lower-ranked 'draft', which previously hid the buttons.
        self.assertEqual(post.status, "draft")

        self._login_portal()
        resp = self.client.get(reverse("client_portal:approval_queue"))
        self.assertEqual(resp.status_code, 200)
        approve_url = reverse("client_portal:approve", kwargs={"post_id": post.id})
        self.assertContains(resp, approve_url)
