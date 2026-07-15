"""Tests for the ?account= scoped composer save paths.

Regression coverage for the bug where opening a post from the calendar with
``?account=<id>`` rendered only that account, so saving (or the 30-second
autosave) deleted every sibling PlatformPost — including already-published
ones, cascading away their PublishLog history.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.publisher.models import PublishLog
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


class AccountScopeTestsBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org = Organization.objects.create(name="Test Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="Test Workspace")
        OrgMembership.objects.create(
            user=self.user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace,
            workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
        )
        self.client.force_login(self.user)

        self.youtube = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="youtube",
            account_platform_id="yt-1",
            account_name="YT Channel",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.tiktok = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-1",
            account_name="janschmitz51",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

        self.post = Post.objects.create(workspace=self.workspace, author=self.user, caption="hello")
        self.yt_pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.youtube,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="yt-video-1",
            published_at=timezone.now(),
        )
        self.tt_pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.tiktok,
            status=PlatformPost.Status.FAILED,
            publish_error="TikTok API error 403: unaudited_client_can_only_post_to_private_accounts",
        )

        self.save_url = reverse(
            "composer:save_post_edit",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id},
        )
        self.autosave_url = reverse(
            "composer:autosave_edit",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id},
        )

    def _payload(self, **overrides):
        payload = {
            "action": "save_draft",
            "title": "Test post",
            "caption": "hello",
            "tags": "",
            "selected_accounts": str(self.tiktok.id),
            "account_scope": str(self.tiktok.id),
        }
        payload.update(overrides)
        return payload


class ScopedSaveTests(AccountScopeTestsBase):
    def test_scoped_save_keeps_published_sibling(self):
        response = self.client.post(self.save_url, data=self._payload())
        self.assertIn(response.status_code, (200, 204, 302))
        self.assertTrue(PlatformPost.objects.filter(id=self.yt_pp.id).exists())
        self.yt_pp.refresh_from_db()
        self.assertEqual(self.yt_pp.status, PlatformPost.Status.PUBLISHED)

    def test_scoped_autosave_keeps_published_sibling_and_logs(self):
        log = PublishLog.objects.create(platform_post=self.yt_pp, attempt_number=1, status_code=200)
        response = self.client.post(
            self.autosave_url,
            data={
                "title": "Test post",
                "caption": "hello",
                "selected_accounts": str(self.tiktok.id),
                "account_scope": str(self.tiktok.id),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PlatformPost.objects.filter(id=self.yt_pp.id).exists())
        self.assertTrue(PublishLog.objects.filter(id=log.id).exists())

    def test_unscoped_deselect_never_deletes_published_row(self):
        # Even the full (unscoped) composer must not hard-delete a published
        # PlatformPost when its account is deselected.
        payload = self._payload()
        del payload["account_scope"]
        response = self.client.post(self.save_url, data=payload)
        self.assertIn(response.status_code, (200, 204, 302))
        self.assertTrue(PlatformPost.objects.filter(id=self.yt_pp.id).exists())

    def test_unscoped_deselect_still_deletes_draft_row(self):
        # Existing behavior preserved: deselecting a draft account removes it.
        self.yt_pp.status = PlatformPost.Status.DRAFT
        self.yt_pp.published_at = None
        self.yt_pp.save(update_fields=["status", "published_at"])
        payload = self._payload()
        del payload["account_scope"]
        response = self.client.post(self.save_url, data=payload)
        self.assertIn(response.status_code, (200, 204, 302))
        self.assertFalse(PlatformPost.objects.filter(id=self.yt_pp.id).exists())

    def test_malformed_scope_rejected_with_400(self):
        # The hidden input is server-rendered from a validated UUID, so a
        # malformed value is a crafted/corrupted request — reject it instead
        # of silently doing partial work.
        response = self.client.post(self.save_url, data=self._payload(account_scope="not-a-uuid"))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(PlatformPost.objects.filter(id=self.yt_pp.id).exists())
        self.assertTrue(PlatformPost.objects.filter(id=self.tt_pp.id).exists())

    def test_malformed_account_param_renders_unscoped(self):
        # ?account=<garbage> must not 500 and must not scope the composer —
        # otherwise the garbage value round-trips into account_scope.
        edit_url = reverse(
            "composer:compose_edit",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id},
        )
        response = self.client.get(edit_url + "?account=not-a-uuid")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertNotIn('name="account_scope"', body)

    def test_valid_account_param_renders_scope_input(self):
        edit_url = reverse(
            "composer:compose_edit",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id},
        )
        response = self.client.get(edit_url + f"?account={self.tiktok.id}")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn('name="account_scope"', body)
        self.assertIn(f'value="{self.tiktok.id}"', body)

    def test_garbage_selected_accounts_entries_ignored(self):
        response = self.client.post(
            self.save_url,
            data=self._payload(selected_accounts=f"not-a-uuid,{self.tiktok.id}", account_scope=str(self.tiktok.id)),
        )
        self.assertIn(response.status_code, (200, 204, 302))
        self.assertTrue(PlatformPost.objects.filter(id=self.tt_pp.id).exists())
        self.assertTrue(PlatformPost.objects.filter(id=self.yt_pp.id).exists())

    def test_scoped_publish_now_does_not_touch_draft_sibling(self):
        self.yt_pp.status = PlatformPost.Status.DRAFT
        self.yt_pp.published_at = None
        self.yt_pp.save(update_fields=["status", "published_at"])
        response = self.client.post(self.save_url, data=self._payload(action="publish_now"))
        self.assertIn(response.status_code, (200, 204, 302))

        self.yt_pp.refresh_from_db()
        self.tt_pp.refresh_from_db()
        self.assertEqual(self.yt_pp.status, PlatformPost.Status.DRAFT)
        self.assertIsNone(self.yt_pp.scheduled_at)
        self.assertEqual(self.tt_pp.status, PlatformPost.Status.SCHEDULED)
        self.assertIsNotNone(self.tt_pp.scheduled_at)

    def test_scoped_publish_now_does_not_reschedule_published_sibling(self):
        response = self.client.post(self.save_url, data=self._payload(action="publish_now"))
        self.assertIn(response.status_code, (200, 204, 302))

        self.yt_pp.refresh_from_db()
        self.assertEqual(self.yt_pp.status, PlatformPost.Status.PUBLISHED)
        self.assertIsNone(self.yt_pp.scheduled_at)


class TikTokExtrasSyncTests(AccountScopeTestsBase):
    def _tiktok_payload(self, **tiktok_fields):
        acc = str(self.tiktok.id)
        payload = self._payload()
        payload.update({f"tiktok_{key}_{acc}": value for key, value in tiktok_fields.items()})
        return payload

    def test_tiktok_settings_round_trip_into_platform_extra(self):
        response = self.client.post(
            self.save_url,
            data=self._tiktok_payload(
                privacy_level="SELF_ONLY",
                allow_comment="true",
                brand_content="true",
                is_aigc="true",
            ),
        )
        self.assertIn(response.status_code, (200, 204, 302))
        self.tt_pp.refresh_from_db()
        extra = self.tt_pp.platform_extra
        self.assertEqual(extra["privacy_level"], "SELF_ONLY")
        self.assertFalse(extra["disable_comment"])
        # Duet/Stitch checkboxes absent from POST → both interactions disabled.
        self.assertTrue(extra["disable_duet"])
        self.assertTrue(extra["disable_stitch"])
        self.assertTrue(extra["brand_content_toggle"])
        self.assertFalse(extra["brand_organic_toggle"])
        self.assertTrue(extra["is_aigc"])

    def test_duet_and_stitch_toggle_independently(self):
        # Duet on, Stitch left off → only stitch disabled. Confirms the two
        # interactions are controlled independently (TikTok's per-interaction rule).
        response = self.client.post(
            self.save_url,
            data=self._tiktok_payload(privacy_level="SELF_ONLY", allow_duet="true"),
        )
        self.assertIn(response.status_code, (200, 204, 302))
        self.tt_pp.refresh_from_db()
        self.assertFalse(self.tt_pp.platform_extra["disable_duet"])
        self.assertTrue(self.tt_pp.platform_extra["disable_stitch"])

    def test_invalid_privacy_level_left_unset(self):
        response = self.client.post(self.save_url, data=self._tiktok_payload(privacy_level="BOGUS"))
        self.assertIn(response.status_code, (200, 204, 302))
        self.tt_pp.refresh_from_db()
        self.assertNotIn("privacy_level", self.tt_pp.platform_extra)

    def test_empty_privacy_value_preserves_saved_choice(self):
        # required-validation bypassed (empty select submitted): the rebuild
        # must keep the previously saved privacy level instead of wiping it.
        self.tt_pp.platform_extra = {"privacy_level": "SELF_ONLY"}
        self.tt_pp.save(update_fields=["platform_extra"])
        response = self.client.post(self.save_url, data=self._tiktok_payload(privacy_level=""))
        self.assertIn(response.status_code, (200, 204, 302))
        self.tt_pp.refresh_from_db()
        self.assertEqual(self.tt_pp.platform_extra["privacy_level"], "SELF_ONLY")

    def test_extras_untouched_when_panel_absent_from_post(self):
        self.tt_pp.platform_extra = {"privacy_level": "SELF_ONLY"}
        self.tt_pp.save(update_fields=["platform_extra"])
        # No tiktok_privacy_level_<id> key in the POST at all.
        response = self.client.post(self.save_url, data=self._payload())
        self.assertIn(response.status_code, (200, 204, 302))
        self.tt_pp.refresh_from_db()
        self.assertEqual(self.tt_pp.platform_extra, {"privacy_level": "SELF_ONLY"})


class PinterestBoardSelectionTests(AccountScopeTestsBase):
    def setUp(self):
        super().setUp()
        self.pinterest = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="pinterest",
            account_platform_id="pin-1",
            account_name="Pinterest",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.pin_pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.pinterest,
            status=PlatformPost.Status.DRAFT,
        )

    def _pinterest_payload(self, **fields):
        acc = str(self.pinterest.id)
        payload = self._payload(selected_accounts=acc, account_scope=acc)
        payload.update({f"pin_{key}_{acc}": value for key, value in fields.items()})
        return payload

    def test_selected_pinterest_account_requires_board(self):
        response = self.client.post(self.save_url, data=self._pinterest_payload())

        self.assertEqual(response.status_code, 400)
        self.assertIn("pinterest_board", response.json()["errors"])

    def test_selected_pinterest_account_saves_board(self):
        response = self.client.post(self.save_url, data=self._pinterest_payload(board_id="board-123"))

        self.assertIn(response.status_code, (200, 204, 302))
        self.pin_pp.refresh_from_db()
        self.assertEqual(self.pin_pp.platform_extra["board_id"], "board-123")

    def test_missing_board_field_preserves_existing_board(self):
        self.pin_pp.platform_extra = {"board_id": "board-123"}
        self.pin_pp.save(update_fields=["platform_extra"])

        response = self.client.post(self.save_url, data=self._pinterest_payload())

        self.assertIn(response.status_code, (200, 204, 302))
        self.pin_pp.refresh_from_db()
        self.assertEqual(self.pin_pp.platform_extra["board_id"], "board-123")


class TikTokComposerDefaultsTests(AccountScopeTestsBase):
    """TikTok's audit requires the composer to ship NO default privacy level and
    NO pre-checked interaction toggles. The defaults live in the Alpine init in
    templates/composer/compose.html, so these guard the rendered expressions
    against silently regressing back to a default.
    """

    def setUp(self):
        super().setUp()
        self.compose_url = reverse("composer:compose", kwargs={"workspace_id": self.workspace.id})

    def test_privacy_renders_with_no_default(self):
        response = self.client.get(self.compose_url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # No pre-selected privacy level (TikTok "no default value" rule)…
        self.assertIn("privacy_level || ''", html)
        self.assertNotIn("privacy_level || 'PUBLIC_TO_EVERYONE'", html)
        # …except when creator-info says SELF_ONLY is the sole legal option for
        # an unaudited app, in which case the form must submit the only valid
        # value instead of falling back to PUBLIC_TO_EVERYONE server-side.
        self.assertIn("opts.length === 1 && opts[0] === 'SELF_ONLY'", html)
        self.assertNotIn("ttPrivacy = opts[0]", html)

    def test_interaction_toggles_unchecked_by_default(self):
        response = self.client.get(self.compose_url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # Comment / Duet / Stitch start unchecked unless a saved extra explicitly
        # enabled them (=== false). A truthy-but-empty platformExtras[accId] ({})
        # must NOT count as "enabled", so each guard checks its field, not the object.
        self.assertIn("ttAllowComment: platformExtras[accId]?.disable_comment === false", html)
        self.assertIn("ttAllowDuet: platformExtras[accId]?.disable_duet === false", html)
        self.assertIn("ttAllowStitch: platformExtras[accId]?.disable_stitch === false", html)
