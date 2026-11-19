"""Instagram "Publish as Story" choice in the composer.

Mirrors the Facebook Reel selector: the composer renders a hidden
``instagram_panel_<id>`` marker for every selected Instagram account, and the
``instagram_post_type_<id>`` select only when exactly one image or video is
attached. Only a submit that carries the marker may change the stored hint.
"""

from django.urls import reverse

from apps.composer.models import PlatformPost, PostMedia
from apps.composer.tests.test_account_scope import AccountScopeTestsBase
from apps.media_library.models import MediaAsset
from apps.social_accounts.models import SocialAccount

OK_STATUSES = (200, 204, 302)


class InstagramStorySettingsTests(AccountScopeTestsBase):
    platform = "instagram"

    def setUp(self):
        super().setUp()
        self.instagram = SocialAccount.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            account_platform_id="ig-1",
            account_name="Instagram Account",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.instagram_pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.instagram,
            status=PlatformPost.Status.DRAFT,
        )
        self.image = self._attach(MediaAsset.MediaType.IMAGE, "story.jpg", post=self.post)

    def _instagram_payload(self, post_type=None):
        account_id = str(self.instagram.id)
        fields = {f"instagram_panel_{account_id}": "1"}
        if post_type is not None:
            fields[f"instagram_post_type_{account_id}"] = post_type
        return self._payload(selected_accounts=account_id, account_scope=account_id, **fields)

    def _save(self, data):
        response = self.client.post(self.save_url, data=data)
        self.assertIn(response.status_code, OK_STATUSES)
        self.instagram_pp.refresh_from_db()

    def test_story_choice_with_one_image_round_trips_into_platform_extra(self):
        self._save(self._instagram_payload("story"))

        self.assertEqual(self.instagram_pp.platform_extra["post_type"], "story")

    def test_story_choice_with_one_video_round_trips_into_platform_extra(self):
        self.post.media_attachments.all().delete()
        self._attach(MediaAsset.MediaType.VIDEO, "story.mp4", post=self.post)

        self._save(self._instagram_payload("story"))

        self.assertEqual(self.instagram_pp.platform_extra["post_type"], "story")

    def test_choosing_feed_clears_the_hint_and_keeps_other_extras(self):
        self.instagram_pp.platform_extra = {"post_type": "story", "location": "x"}
        self.instagram_pp.save(update_fields=["platform_extra"])

        self._save(self._instagram_payload("feed"))

        self.assertEqual(self.instagram_pp.platform_extra, {"location": "x"})

    def test_story_choice_is_rejected_for_multiple_attachments(self):
        """Two attachments are a carousel; a Story takes exactly one."""
        image_2 = self._attach(MediaAsset.MediaType.IMAGE, "story-2.jpg")
        PostMedia.objects.create(post=self.post, media_asset=image_2, position=1)

        self._save(self._instagram_payload("story"))

        self.assertNotIn("post_type", self.instagram_pp.platform_extra or {})

    def test_story_choice_is_cleared_when_media_is_removed(self):
        self.instagram_pp.platform_extra = {"post_type": "story"}
        self.instagram_pp.save(update_fields=["platform_extra"])
        self.post.media_attachments.all().delete()

        self._save(self._instagram_payload())

        self.assertEqual(self.instagram_pp.platform_extra, {})

    def test_a_save_without_the_panel_leaves_the_choice_untouched(self):
        self.instagram_pp.platform_extra = {"post_type": "story"}
        self.instagram_pp.save(update_fields=["platform_extra"])
        account_id = str(self.instagram.id)

        self._save(self._payload(selected_accounts=account_id, account_scope=account_id))

        self.assertEqual(self.instagram_pp.platform_extra, {"post_type": "story"})

    def test_an_unknown_value_is_not_stored(self):
        self._save(self._instagram_payload("reel"))

        self.assertNotIn("post_type", self.instagram_pp.platform_extra or {})

    def test_the_composer_renders_the_story_selector(self):
        url = reverse("composer:compose_edit", kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "'instagram_post_type_' + accId")
        self.assertContains(response, "'instagram_panel_' + accId")
        self.assertContains(response, '<option value="story">Story</option>', html=True)


class InstagramLoginStorySettingsTests(InstagramStorySettingsTests):
    """Instagram (Direct) connects without Facebook but publishes Stories the same way."""

    platform = "instagram_login"
