"""Composer read-only gating — action bar + the save/autosave endpoints behind it.

A post that is live (or mid-publish) shows a read-only banner. These tests pin
the two halves that banner promises: the action bar stops offering to change the
post, and the write endpoints refuse to, so the promise survives a crafted POST
or a stale tab. Clone stays the escape hatch, and Delete stays available because
the composer is the only place a published post can be deleted.

Scoping matters throughout: opened with ``?account=`` the composer shows one
channel, so read-only must reflect *that* child. A failed channel on a
partially-published post stays fully workable.
"""

import re

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

# Distinguishing substrings for the action-bar controls under test.
PUBLISH_BTN = 'id="publish-action-btn"'
PUBLISH_ANCHOR = 'id="publish-anchor"'
SAVE_DRAFT_BTN = 'value="save_draft"'
SUBMIT_BTN = 'value="submit_for_approval"'
DELETE_BTN = "open-delete-modal"
AUTOSAVE_TRIGGER = 'id="autosave-trigger"'


def _make_workspace():
    org = Organization.objects.create(name="Org")
    ws = Workspace.objects.create(organization=org, name="WS", timezone="Europe/Berlin")
    primary = SocialAccount.objects.create(
        workspace=ws,
        platform="linkedin_personal",
        account_platform_id="li-1",
        account_name="Primary",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    secondary = SocialAccount.objects.create(
        workspace=ws,
        platform="tiktok",
        account_platform_id="tt-1",
        account_name="Secondary",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    return org, ws, primary, secondary


class ReadonlyComposerTestsBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org, self.ws, self.primary, self.secondary = _make_workspace()
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=self.user, workspace=self.ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
        )
        self.client.force_login(self.user)

    def _make_post(self, primary_status, secondary_status=None):
        """A post whose primary child sits in ``primary_status``."""
        post = Post.objects.create(workspace=self.ws, author=self.user, caption="original caption")
        PlatformPost.objects.create(post=post, social_account=self.primary, status=primary_status)
        if secondary_status is not None:
            PlatformPost.objects.create(post=post, social_account=self.secondary, status=secondary_status)
        return post

    def _compose(self, post, account=None):
        url = reverse("composer:compose_edit", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        if account is not None:
            url = f"{url}?account={account.id}"
        return self.client.get(url)

    def _save_url(self, post):
        return reverse("composer:save_post_edit", kwargs={"workspace_id": self.ws.id, "post_id": post.id})

    def _autosave_url(self, post):
        return reverse("composer:autosave_edit", kwargs={"workspace_id": self.ws.id, "post_id": post.id})


class ActionBarGatingTests(ReadonlyComposerTestsBase):
    """What the composer offers, per derived post status."""

    def test_draft_offers_publish_and_save(self):
        resp = self._compose(self._make_post(PlatformPost.Status.DRAFT))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["post_is_readonly"])
        body = resp.content.decode("utf-8")
        self.assertIn(PUBLISH_BTN, body)
        self.assertIn(SAVE_DRAFT_BTN, body)
        self.assertIn(AUTOSAVE_TRIGGER, body)

    def test_published_hides_publish_and_save(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self._compose(post)
        self.assertTrue(resp.context["post_is_readonly"])
        body = resp.content.decode("utf-8")
        self.assertNotIn(PUBLISH_BTN, body)
        self.assertNotIn(PUBLISH_ANCHOR, body)
        self.assertNotIn(SAVE_DRAFT_BTN, body)
        # The banner still explains why, and offers the escape hatch.
        self.assertIn("read-only", body)
        self.assertIn(reverse("composer:clone_post", kwargs={"workspace_id": self.ws.id, "post_id": post.id}), body)

    def test_publishing_hides_publish_and_save(self):
        resp = self._compose(self._make_post(PlatformPost.Status.PUBLISHING))
        self.assertTrue(resp.context["post_is_readonly"])
        body = resp.content.decode("utf-8")
        self.assertNotIn(PUBLISH_BTN, body)
        self.assertNotIn(SAVE_DRAFT_BTN, body)

    def test_partially_published_hides_publish_and_save(self):
        # published + failed derives to "partially_published".
        post = self._make_post(PlatformPost.Status.PUBLISHED, PlatformPost.Status.FAILED)
        resp = self._compose(post)
        self.assertTrue(resp.context["post_is_readonly"])
        body = resp.content.decode("utf-8")
        self.assertNotIn(PUBLISH_BTN, body)
        self.assertNotIn(SAVE_DRAFT_BTN, body)

    def test_readonly_post_keeps_delete(self):
        # The composer is the only place a published post can be deleted, so the
        # button must survive the read-only gating.
        body = self._compose(self._make_post(PlatformPost.Status.PUBLISHED)).content.decode("utf-8")
        self.assertIn(DELETE_BTN, body)

    def test_readonly_post_stops_autosaving(self):
        body = self._compose(self._make_post(PlatformPost.Status.PUBLISHED)).content.decode("utf-8")
        self.assertNotIn(AUTOSAVE_TRIGGER, body)

    def test_readonly_post_hides_submit_for_approval(self):
        # With approvals on, a published post must not offer to re-enter the
        # workflow — show_submit_button would otherwise be True.
        self.ws.approval_workflow_mode = "internal"
        self.ws.save(update_fields=["approval_workflow_mode"])
        body = self._compose(self._make_post(PlatformPost.Status.PUBLISHED)).content.decode("utf-8")
        self.assertNotIn(SUBMIT_BTN, body)

    def test_draft_still_offers_submit_for_approval(self):
        self.ws.approval_workflow_mode = "internal"
        self.ws.save(update_fields=["approval_workflow_mode"])
        body = self._compose(self._make_post(PlatformPost.Status.DRAFT)).content.decode("utf-8")
        self.assertIn(SUBMIT_BTN, body)

    def test_scoped_to_failed_child_is_not_readonly(self):
        # Opened on the failed channel of a partially-published post, the
        # composer is showing an editable thing — the published sibling must not
        # lock it down.
        post = self._make_post(PlatformPost.Status.PUBLISHED, PlatformPost.Status.FAILED)
        resp = self._compose(post, account=self.secondary)
        self.assertFalse(resp.context["post_is_readonly"])
        body = resp.content.decode("utf-8")
        self.assertIn(PUBLISH_BTN, body)
        self.assertIn(SAVE_DRAFT_BTN, body)

    def test_scoped_to_published_child_is_readonly(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED, PlatformPost.Status.FAILED)
        resp = self._compose(post, account=self.primary)
        self.assertTrue(resp.context["post_is_readonly"])
        self.assertNotIn(PUBLISH_BTN, resp.content.decode("utf-8"))

    def test_scope_naming_an_unrelated_account_stays_readonly(self):
        # secondary owns no row on this post: the scoped list is empty, which
        # must fall back to the aggregate rather than reopening a live post.
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self._compose(post, account=self.secondary)
        self.assertTrue(resp.context["post_is_readonly"])
        body = resp.content.decode("utf-8")
        self.assertNotIn(PUBLISH_BTN, body)
        self.assertNotIn(SAVE_DRAFT_BTN, body)

    def test_uppercased_scope_still_matches_its_child(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED, PlatformPost.Status.FAILED)
        url = reverse("composer:compose_edit", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        resp = self.client.get(f"{url}?account={str(self.secondary.id).upper()}")
        # Matched the failed child despite the casing, so the composer stays live.
        self.assertFalse(resp.context["post_is_readonly"])
        self.assertIn(PUBLISH_BTN, resp.content.decode("utf-8"))

    def test_scoped_view_names_the_live_sibling(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED, PlatformPost.Status.FAILED)
        resp = self._compose(post, account=self.secondary)
        self.assertFalse(resp.context["post_is_readonly"])
        self.assertEqual([pp.social_account_id for pp in resp.context["live_siblings"]], [self.primary.id])
        self.assertIn("Already published on", resp.content.decode("utf-8"))

    def test_unscoped_view_has_no_live_sibling_notice(self):
        post = self._make_post(PlatformPost.Status.DRAFT, PlatformPost.Status.PUBLISHED)
        resp = self._compose(post)
        self.assertEqual(list(resp.context["live_siblings"]), [])
        self.assertNotIn("Already published on", resp.content.decode("utf-8"))

    def test_only_the_form_itself_opts_out_of_the_error_toast(self):
        # base.html checks data-no-error-toast on the requesting element, not its
        # ancestors, so exactly one element may carry it: the form, whose
        # onFormSaved renders every failure inline. If it ever spreads to a
        # wrapper, the nested Clone button and template picker — which have no
        # handler of their own — start failing silently.
        body = self._compose(self._make_post(PlatformPost.Status.PUBLISHED)).content.decode("utf-8")
        # Bare attribute uses only — base.html's own handler mentions the name
        # as a quoted string, which is not an opt-out.
        attribute_uses = re.findall(r"""(?<!['"])data-no-error-toast(?!['"])""", body)
        self.assertEqual(len(attribute_uses), 1)
        form_tag = body[body.index('<form id="composer-form"') :]
        self.assertIn("data-no-error-toast", form_tag[: form_tag.index(">")])


class ReadonlyWriteGuardTests(ReadonlyComposerTestsBase):
    """The endpoints refuse what the action bar stopped offering."""

    def _payload(self, **overrides):
        payload = {
            "action": "save_draft",
            "title": "Rewritten",
            "caption": "rewritten caption",
            "tags": "",
            "selected_accounts": str(self.primary.id),
        }
        payload.update(overrides)
        return payload

    def test_publish_now_on_published_post_is_rejected(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self.client.post(self._save_url(post), data=self._payload(action="publish_now"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("status", resp.json()["errors"])
        post.refresh_from_db()
        # The bug this closes: publish_now used to re-stamp scheduled_at.
        self.assertIsNone(post.scheduled_at)
        self.assertEqual(post.caption, "original caption")

    def test_schedule_on_published_post_is_rejected(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self.client.post(
            self._save_url(post),
            data=self._payload(action="schedule", scheduled_date="2099-01-01", scheduled_time="09:00"),
        )
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertIsNone(post.scheduled_at)

    def test_save_draft_on_published_post_is_rejected(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self.client.post(self._save_url(post), data=self._payload())
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertEqual(post.caption, "original caption")

    def test_post_without_action_on_published_post_is_rejected(self):
        # ``action`` defaults to save_draft server-side, so an Enter keypress or
        # an API client omitting it must not slip past the guard.
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        payload = self._payload()
        del payload["action"]
        resp = self.client.post(self._save_url(post), data=payload)
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertEqual(post.caption, "original caption")

    def test_save_on_publishing_post_is_rejected(self):
        post = self._make_post(PlatformPost.Status.PUBLISHING)
        resp = self.client.post(self._save_url(post), data=self._payload())
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertEqual(post.caption, "original caption")

    def test_autosave_on_published_post_is_a_no_op(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self.client.post(
            self._autosave_url(post),
            data={"title": "Rewritten", "caption": "rewritten caption", "selected_accounts": str(self.primary.id)},
        )
        # 200, not 4xx: the response swaps into #autosave-status, so an error
        # status would fire the global toast every 30 seconds.
        self.assertEqual(resp.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.caption, "original caption")

    def test_draft_save_still_works(self):
        post = self._make_post(PlatformPost.Status.DRAFT)
        resp = self.client.post(self._save_url(post), data=self._payload())
        self.assertIn(resp.status_code, (200, 204, 302))
        post.refresh_from_db()
        self.assertEqual(post.caption, "rewritten caption")

    def test_scoped_save_on_partially_published_post_still_works(self):
        # The guard must not overreach: with the composer scoped to the failed
        # channel there is still something to write.
        post = self._make_post(PlatformPost.Status.PUBLISHED, PlatformPost.Status.FAILED)
        resp = self.client.post(
            self._save_url(post),
            data=self._payload(
                selected_accounts=str(self.secondary.id),
                account_scope=str(self.secondary.id),
            ),
        )
        self.assertIn(resp.status_code, (200, 204, 302))
        post.refresh_from_db()
        self.assertEqual(post.caption, "rewritten caption")

    def test_scoped_save_on_published_child_is_rejected(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED, PlatformPost.Status.FAILED)
        resp = self.client.post(
            self._save_url(post),
            data=self._payload(
                selected_accounts=str(self.primary.id),
                account_scope=str(self.primary.id),
            ),
        )
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertEqual(post.caption, "original caption")

    def test_uppercased_scope_cannot_slip_past_the_guard(self):
        # uuid.UUID() accepts any case, but str() of one is always lowercase —
        # comparing strings would match no child and fall open.
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self.client.post(
            self._save_url(post),
            data=self._payload(action="publish_now", account_scope=str(self.primary.id).upper()),
        )
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertIsNone(post.scheduled_at)
        self.assertEqual(post.caption, "original caption")

    def test_scope_naming_an_unrelated_account_cannot_slip_past_the_guard(self):
        # secondary has no PlatformPost on this post, so the scoped child list is
        # empty. An empty list must not read as "nothing published here".
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self.client.post(
            self._save_url(post),
            data=self._payload(action="publish_now", account_scope=str(self.secondary.id)),
        )
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertIsNone(post.scheduled_at)
        self.assertEqual(post.caption, "original caption")

    def test_autosave_with_unrelated_scope_on_published_post_is_a_no_op(self):
        post = self._make_post(PlatformPost.Status.PUBLISHED)
        resp = self.client.post(
            self._autosave_url(post),
            data={"title": "Rewritten", "caption": "rewritten caption", "account_scope": str(self.secondary.id)},
        )
        self.assertEqual(resp.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.caption, "original caption")
