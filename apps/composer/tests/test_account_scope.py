"""Tests for the ?account= scoped composer save paths.

Regression coverage for the bug where opening a post from the calendar with
``?account=<id>`` rendered only that account, so saving (or the 30-second
autosave) deleted every sibling PlatformPost — including already-published
ones, cascading away their PublishLog history.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post, PostMedia
from apps.media_library.models import MediaAsset
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

    def _attach(self, media_type, filename, post=None):
        asset = MediaAsset.objects.create(
            organization=self.org,
            workspace=self.workspace,
            uploaded_by=self.user,
            file=f"test/{filename}",
            filename=filename,
            media_type=media_type,
            mime_type="video/mp4" if media_type == MediaAsset.MediaType.VIDEO else "image/jpeg",
        )
        if post is not None:
            PostMedia.objects.create(post=post, media_asset=asset)
        return asset

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
        # TikTok only publishes video, and the composer refuses to schedule it
        # without one.
        self._attach(MediaAsset.MediaType.VIDEO, "clip.mp4", post=self.post)
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
        self._attach(MediaAsset.MediaType.VIDEO, "clip.mp4", post=self.post)
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


class FacebookVideoSettingsTests(AccountScopeTestsBase):
    def setUp(self):
        super().setUp()
        self.facebook = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="fb-page-1",
            account_name="Facebook Page",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.facebook_pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.facebook,
            status=PlatformPost.Status.DRAFT,
        )
        self.video = MediaAsset.objects.create(
            organization=self.org,
            workspace=self.workspace,
            uploaded_by=self.user,
            file="test/facebook-reel.mp4",
            filename="facebook-reel.mp4",
            media_type=MediaAsset.MediaType.VIDEO,
            mime_type="video/mp4",
        )
        PostMedia.objects.create(post=self.post, media_asset=self.video)

    def _facebook_payload(self, post_type=None):
        """A composer submit for the Facebook account.

        The hidden ``facebook_panel_<id>`` marker is what the composer renders
        for every selected Facebook account, video attached or not; the select
        itself is only submitted when exactly one video is attached.
        """
        account_id = str(self.facebook.id)
        fields = {f"facebook_panel_{account_id}": "1"}
        if post_type is not None:
            fields[f"facebook_post_type_{account_id}"] = post_type
        return self._payload(
            selected_accounts=account_id,
            account_scope=account_id,
            **fields,
        )

    def test_facebook_reel_choice_round_trips_into_platform_extra(self):
        response = self.client.post(self.save_url, data=self._facebook_payload("reel"))

        self.assertIn(response.status_code, (200, 204, 302))
        self.facebook_pp.refresh_from_db()
        self.assertEqual(self.facebook_pp.platform_extra["post_type"], "reel")

    def test_choosing_regular_video_clears_the_hint_rather_than_recording_it(self):
        """A lone video already infers VIDEO, so the hint would only restate it.

        Recording it could only go wrong: swap the attachment for an image
        through the media endpoints and a stored "video" would still route the
        image to Facebook's video endpoint.
        """
        self.facebook_pp.platform_extra = {"post_type": "reel", "audience": "public"}
        self.facebook_pp.save(update_fields=["platform_extra"])

        response = self.client.post(self.save_url, data=self._facebook_payload("video"))

        self.assertIn(response.status_code, (200, 204, 302))
        self.facebook_pp.refresh_from_db()
        self.assertEqual(self.facebook_pp.platform_extra, {"audience": "public"})

    def test_facebook_reel_choice_is_cleared_when_video_is_removed(self):
        self.facebook_pp.platform_extra = {"post_type": "reel", "audience": "public"}
        self.facebook_pp.save(update_fields=["platform_extra"])
        self.post.media_attachments.all().delete()

        response = self.client.post(self.save_url, data=self._facebook_payload())

        self.assertIn(response.status_code, (200, 204, 302))
        self.facebook_pp.refresh_from_db()
        self.assertEqual(self.facebook_pp.platform_extra, {"audience": "public"})

    def test_a_save_without_the_panel_leaves_the_choice_untouched(self):
        """A save that never rendered the panel must not rewrite its extras.

        Same guarantee the TikTok branch spells out: only the form that showed
        the control may change what the control controls.
        """
        self.facebook_pp.platform_extra = {"post_type": "reel"}
        self.facebook_pp.save(update_fields=["platform_extra"])
        account_id = str(self.facebook.id)

        response = self.client.post(
            self.save_url,
            data=self._payload(selected_accounts=account_id, account_scope=account_id),
        )

        self.assertIn(response.status_code, (200, 204, 302))
        self.facebook_pp.refresh_from_db()
        self.assertEqual(self.facebook_pp.platform_extra, {"post_type": "reel"})

    def test_facebook_reel_choice_is_rejected_for_multiple_attachments(self):
        image = MediaAsset.objects.create(
            organization=self.org,
            workspace=self.workspace,
            uploaded_by=self.user,
            file="test/facebook-image.jpg",
            filename="facebook-image.jpg",
            media_type=MediaAsset.MediaType.IMAGE,
            mime_type="image/jpeg",
        )
        PostMedia.objects.create(post=self.post, media_asset=image, position=1)

        response = self.client.post(self.save_url, data=self._facebook_payload("reel"))

        self.assertIn(response.status_code, (200, 204, 302))
        self.facebook_pp.refresh_from_db()
        self.assertNotIn("post_type", self.facebook_pp.platform_extra)


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


class VideoOnlyPlatformTests(AccountScopeTestsBase):
    """TikTok and YouTube publish nothing but video, so scheduling a post
    without one only sets up a failure after its other platforms went out."""

    def test_scheduling_tiktok_without_a_video_is_refused(self):
        self._attach(MediaAsset.MediaType.IMAGE, "photo.jpg", post=self.post)

        response = self.client.post(self.save_url, data=self._payload(action="publish_now"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["media"],
            "TikTok can only publish videos. Add a video to this post, or deselect that account.",
        )
        self.tt_pp.refresh_from_db()
        self.assertEqual(self.tt_pp.status, PlatformPost.Status.FAILED)

    def test_every_committing_action_is_checked(self):
        for action in ("schedule", "add_to_queue", "add_to_queue_priority", "submit_for_approval"):
            with self.subTest(action=action):
                response = self.client.post(self.save_url, data=self._payload(action=action))
                self.assertEqual(response.status_code, 400)
                self.assertIn("media", response.json()["errors"])

    def test_both_video_platforms_are_named(self):
        both = f"{self.tiktok.id},{self.youtube.id}"

        response = self.client.post(self.save_url, data=self._payload(action="publish_now", selected_accounts=both))

        self.assertEqual(response.status_code, 400)
        self.assertIn("TikTok and YouTube can only publish videos", response.json()["errors"]["media"])
        self.assertIn("those accounts", response.json()["errors"]["media"])

    def test_a_draft_may_wait_for_its_video(self):
        response = self.client.post(self.save_url, data=self._payload(action="save_draft"))

        self.assertIn(response.status_code, (200, 204, 302))

    def test_scheduling_with_a_video_attached_is_allowed(self):
        self._attach(MediaAsset.MediaType.IMAGE, "photo.jpg", post=self.post)
        self._attach(MediaAsset.MediaType.VIDEO, "clip.mp4", post=self.post)

        response = self.client.post(self.save_url, data=self._payload(action="publish_now"))

        self.assertIn(response.status_code, (200, 204, 302))
        self.tt_pp.refresh_from_db()
        self.assertEqual(self.tt_pp.status, PlatformPost.Status.SCHEDULED)

    def test_other_platforms_are_not_checked(self):
        facebook = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="fb-1",
            account_name="Page",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        acc = str(facebook.id)

        response = self.client.post(
            self.save_url,
            data=self._payload(action="publish_now", selected_accounts=acc, account_scope=acc),
        )

        self.assertIn(response.status_code, (200, 204, 302))

    def test_a_new_post_counts_the_video_waiting_in_the_session(self):
        """A post that has never been saved holds its uploads in the session."""
        video = self._attach(MediaAsset.MediaType.VIDEO, "clip.mp4")
        session = self.client.session
        session[f"pending_media_{self.workspace.id}"] = [str(video.id)]
        session.save()
        new_post_url = reverse("composer:save_post", kwargs={"workspace_id": self.workspace.id})
        payload = self._payload(action="publish_now")
        payload.pop("account_scope")

        response = self.client.post(new_post_url, data=payload)

        self.assertIn(response.status_code, (200, 204, 302))

    def test_a_new_post_without_a_video_is_refused(self):
        new_post_url = reverse("composer:save_post", kwargs={"workspace_id": self.workspace.id})
        payload = self._payload(action="publish_now")
        payload.pop("account_scope")

        response = self.client.post(new_post_url, data=payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("media", response.json()["errors"])

    def _transition(self, target):
        url = reverse(
            "composer:transition_platform_post",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id, "platform_post_id": self.tt_pp.id},
        )
        return self.client.post(url, data={"target_status": target})

    def test_retrying_a_failed_row_without_a_video_is_refused(self):
        """The per-account transition skips save_post, so it checks on its own."""
        response = self._transition("scheduled")

        self.assertEqual(response.status_code, 400)
        self.assertIn("TikTok can only publish videos", response.json()["error"])
        self.tt_pp.refresh_from_db()
        self.assertEqual(self.tt_pp.status, PlatformPost.Status.FAILED)

    def test_retrying_a_failed_row_with_a_video_is_allowed(self):
        self._attach(MediaAsset.MediaType.VIDEO, "clip.mp4", post=self.post)

        response = self._transition("scheduled")

        self.assertEqual(response.status_code, 200)
        self.tt_pp.refresh_from_db()
        self.assertEqual(self.tt_pp.status, PlatformPost.Status.SCHEDULED)

    def _remove(self, attachment):
        url = reverse(
            "composer:remove_media",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id, "media_id": attachment.id},
        )
        return self.client.post(url)

    def _schedule_tiktok(self):
        self.tt_pp.status = PlatformPost.Status.SCHEDULED
        self.tt_pp.scheduled_at = timezone.now() + timedelta(days=1)
        self.tt_pp.save(update_fields=["status", "scheduled_at"])

    def test_removing_the_last_video_of_a_scheduled_tiktok_post_is_refused(self):
        video = self._attach(MediaAsset.MediaType.VIDEO, "clip.mp4", post=self.post)
        self._schedule_tiktok()

        response = self._remove(PostMedia.objects.get(media_asset=video))

        self.assertEqual(response.status_code, 400)
        self.assertIn("scheduled to TikTok, which needs a video", response.content.decode())
        self.assertTrue(PostMedia.objects.filter(media_asset=video).exists())

    def test_removing_one_of_two_videos_is_allowed(self):
        first = self._attach(MediaAsset.MediaType.VIDEO, "a.mp4", post=self.post)
        self._attach(MediaAsset.MediaType.VIDEO, "b.mp4", post=self.post)
        self._schedule_tiktok()

        response = self._remove(PostMedia.objects.get(media_asset=first))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(PostMedia.objects.filter(media_asset=first).exists())

    def test_removing_the_video_of_an_unscheduled_post_is_allowed(self):
        video = self._attach(MediaAsset.MediaType.VIDEO, "clip.mp4", post=self.post)

        response = self._remove(PostMedia.objects.get(media_asset=video))

        self.assertEqual(response.status_code, 200)

    def test_a_video_with_no_stored_file_does_not_count(self):
        """The publisher skips attachments with no file, so the check must too."""
        empty = self._attach(MediaAsset.MediaType.VIDEO, "gone.mp4", post=self.post)
        MediaAsset.objects.filter(pk=empty.pk).update(file="")

        response = self.client.post(self.save_url, data=self._payload(action="publish_now"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("media", response.json()["errors"])


class CsvImportPublishabilityTests(AccountScopeTestsBase):
    """A CSV row carries no media and no Pinterest board, so a dated row for
    TikTok, YouTube or Pinterest can never publish — it is kept as a draft on
    its date instead of being scheduled to fail."""

    def setUp(self):
        super().setUp()
        self.linkedin = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-1",
            account_name="LinkedIn",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

    def _import(self, platforms):
        session = self.client.session
        session[f"csv_import_{self.workspace.id}"] = {"rows": [["From the CSV", "2026-12-01", "10:00", platforms]]}
        session[f"csv_mapping_{self.workspace.id}"] = {"caption": 0, "date": 1, "time": 2, "platforms": 3}
        session.save()
        return self.client.post(reverse("composer:csv_confirm_import", kwargs={"workspace_id": self.workspace.id}))

    def _row(self, account):
        return PlatformPost.objects.get(post__caption="From the CSV", social_account=account)

    def test_rows_that_cannot_publish_are_kept_as_drafts_on_their_date(self):
        response = self._import("tiktok,linkedin_personal")

        self.assertEqual(response.status_code, 200)
        tiktok_row = self._row(self.tiktok)
        self.assertEqual(tiktok_row.status, PlatformPost.Status.DRAFT)
        self.assertIsNotNone(tiktok_row.scheduled_at)
        self.assertEqual(self._row(self.linkedin).status, PlatformPost.Status.SCHEDULED)
        self.assertContains(response, "1 TikTok post was kept as draft")

    def test_an_undated_row_is_a_draft_either_way_and_reports_nothing(self):
        session = self.client.session
        session[f"csv_import_{self.workspace.id}"] = {"rows": [["From the CSV", "tiktok"]]}
        session[f"csv_mapping_{self.workspace.id}"] = {"caption": 0, "platforms": 1}
        session.save()

        response = self.client.post(reverse("composer:csv_confirm_import", kwargs={"workspace_id": self.workspace.id}))

        self.assertEqual(self._row(self.tiktok).status, PlatformPost.Status.DRAFT)
        self.assertNotContains(response, "kept as draft")


class RequiredMediaTests(PinterestBoardSelectionTests):
    """Pinterest and Instagram need an image or a video; their providers
    refuse a post with nothing attached before calling out."""

    def test_scheduling_a_pin_with_a_board_but_no_media_is_refused(self):
        response = self.client.post(
            self.save_url, data=self._pinterest_payload(board_id="board-1") | {"action": "publish_now"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["media"],
            "Pinterest needs an image or a video. Add an image or a video to this post, or deselect that account.",
        )

    def test_a_pin_with_an_image_can_be_scheduled(self):
        self._attach(MediaAsset.MediaType.IMAGE, "photo.jpg", post=self.post)

        response = self.client.post(
            self.save_url, data=self._pinterest_payload(board_id="board-1") | {"action": "publish_now"}
        )

        self.assertIn(response.status_code, (200, 204, 302))

    def test_tiktok_and_pinterest_together_ask_for_a_video(self):
        both = f"{self.tiktok.id},{self.pinterest.id}"
        payload = self._pinterest_payload(board_id="board-1") | {
            "action": "publish_now",
            "selected_accounts": both,
        }
        payload.pop("account_scope")

        response = self.client.post(self.save_url, data=payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["media"],
            "TikTok can only publish videos. Pinterest needs an image or a video. "
            "Add a video to this post, or deselect those accounts.",
        )

    def test_removing_the_last_image_of_a_scheduled_pin_is_refused(self):
        image = self._attach(MediaAsset.MediaType.IMAGE, "photo.jpg", post=self.post)
        self.pin_pp.status = PlatformPost.Status.SCHEDULED
        self.pin_pp.platform_extra = {"board_id": "board-1"}
        self.pin_pp.save(update_fields=["status", "platform_extra"])
        url = reverse(
            "composer:remove_media",
            kwargs={
                "workspace_id": self.workspace.id,
                "post_id": self.post.id,
                "media_id": PostMedia.objects.get(media_asset=image).id,
            },
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        self.assertIn("scheduled to Pinterest, which needs an image or a video", response.content.decode())


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


class InstagramSettingsTests(AccountScopeTestsBase):
    def setUp(self):
        super().setUp()
        self.instagram = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="instagram_login",
            account_platform_id="ig-1",
            account_name="Instagram Account",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.instagram_pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.instagram,
            status=PlatformPost.Status.DRAFT,
        )
        self._attach(MediaAsset.MediaType.VIDEO, "reel.mp4", post=self.post)

    def _instagram_payload(self, **instagram_fields):
        """A composer submit for the Instagram account.

        The hidden ``instagram_panel_<id>`` marker is rendered for every
        selected Instagram account; the cover input only while a single video
        is attached, and the toggle only submits when switched on.
        """
        account_id = str(self.instagram.id)
        fields = {f"instagram_panel_{account_id}": "1"}
        fields.update({f"instagram_{key}_{account_id}": value for key, value in instagram_fields.items()})
        return self._payload(selected_accounts=account_id, account_scope=account_id, **fields)

    def test_ai_disclosure_and_cover_round_trip_into_platform_extra(self):
        response = self.client.post(
            self.save_url,
            data=self._instagram_payload(is_ai_generated="true", video_cover_timestamp_ms="22400"),
        )

        self.assertIn(response.status_code, (200, 204, 302))
        self.instagram_pp.refresh_from_db()
        self.assertEqual(
            self.instagram_pp.platform_extra,
            {"is_ai_generated": True, "video_cover_timestamp_ms": 22400},
        )

    def test_switching_the_disclosure_off_removes_it_and_keeps_other_extras(self):
        self.instagram_pp.platform_extra = {"is_ai_generated": True, "audience": "public"}
        self.instagram_pp.save(update_fields=["platform_extra"])

        response = self.client.post(self.save_url, data=self._instagram_payload())

        self.assertIn(response.status_code, (200, 204, 302))
        self.instagram_pp.refresh_from_db()
        self.assertEqual(self.instagram_pp.platform_extra, {"audience": "public"})

    def test_an_invalid_cover_clears_the_stored_one(self):
        self.instagram_pp.platform_extra = {"video_cover_timestamp_ms": 1000}
        self.instagram_pp.save(update_fields=["platform_extra"])

        response = self.client.post(self.save_url, data=self._instagram_payload(video_cover_timestamp_ms="²"))

        self.assertIn(response.status_code, (200, 204, 302))
        self.instagram_pp.refresh_from_db()
        self.assertNotIn("video_cover_timestamp_ms", self.instagram_pp.platform_extra)

    def test_the_cover_is_dropped_when_the_post_is_not_a_single_video(self):
        """A second attachment makes it a carousel: an offset into one of its
        videos would be a stale choice, not a cover."""
        self._attach(MediaAsset.MediaType.IMAGE, "extra.jpg", post=self.post)

        response = self.client.post(
            self.save_url,
            data=self._instagram_payload(is_ai_generated="true", video_cover_timestamp_ms="22400"),
        )

        self.assertIn(response.status_code, (200, 204, 302))
        self.instagram_pp.refresh_from_db()
        self.assertEqual(self.instagram_pp.platform_extra, {"is_ai_generated": True})

    def test_a_save_without_the_panel_leaves_the_extras_untouched(self):
        self.instagram_pp.platform_extra = {"is_ai_generated": True, "video_cover_timestamp_ms": 22400}
        self.instagram_pp.save(update_fields=["platform_extra"])
        account_id = str(self.instagram.id)

        response = self.client.post(
            self.save_url,
            data=self._payload(selected_accounts=account_id, account_scope=account_id),
        )

        self.assertIn(response.status_code, (200, 204, 302))
        self.instagram_pp.refresh_from_db()
        self.assertEqual(
            self.instagram_pp.platform_extra,
            {"is_ai_generated": True, "video_cover_timestamp_ms": 22400},
        )

    def test_the_facebook_login_connection_gets_the_same_panel(self):
        self.instagram.platform = "instagram"
        self.instagram.save(update_fields=["platform"])

        response = self.client.post(self.save_url, data=self._instagram_payload(is_ai_generated="true"))

        self.assertIn(response.status_code, (200, 204, 302))
        self.instagram_pp.refresh_from_db()
        self.assertEqual(self.instagram_pp.platform_extra, {"is_ai_generated": True})

    def test_the_composer_renders_the_panel_off_by_default(self):
        """The disclosure is the creator's statement, so it starts off unless a
        saved extra turned it on; the inputs carry the names the view reads."""
        response = self.client.get(reverse("composer:compose", kwargs={"workspace_id": self.workspace.id}))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("igAiGenerated: !!platformExtras[accId]?.is_ai_generated", html)
        self.assertIn(":name=\"'instagram_panel_' + accId\"", html)
        self.assertIn(":name=\"'instagram_is_ai_generated_' + accId\"", html)
        self.assertIn(":name=\"'instagram_video_cover_timestamp_ms_' + accId\"", html)
