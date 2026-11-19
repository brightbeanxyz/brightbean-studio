"""Publishing side of the Instagram Story choice.

The composer stores ``platform_extra["post_type"] = "story"``; the engine must
only honour it while exactly one image or video is attached, and must never
queue a first comment on a Story (Stories take no comments).
"""

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.publisher.engine import PublishEngine
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers.types import PostType


class StoryHintMatchesMediaTest(SimpleTestCase):
    def _resolve(self, media_count, first_media_type, platform="instagram"):
        return PublishEngine._resolve_post_type(
            platform=platform,
            platform_extra={"post_type": "story"},
            media_count=media_count,
            first_media_type=first_media_type,
        )

    def test_one_image_or_video_publishes_as_a_story(self):
        for media_type in ("image", "video"):
            for platform in ("instagram", "instagram_login"):
                with self.subTest(media_type=media_type, platform=platform):
                    self.assertEqual(self._resolve(1, media_type, platform), PostType.STORY)

    def test_a_stale_story_hint_with_two_attachments_falls_back_to_a_carousel(self):
        self.assertEqual(self._resolve(2, "image"), PostType.CAROUSEL)

    def test_a_stale_story_hint_without_media_is_ignored(self):
        self.assertEqual(self._resolve(0, None), PostType.TEXT)


class StoryFirstCommentTest(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Org")
        workspace = Workspace.objects.create(organization=org, name="WS")
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="instagram",
            account_platform_id="ig-1",
            account_name="IG",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        post = Post.objects.create(workspace=workspace, caption="hi", first_comment="Read more")
        self.platform_post = PlatformPost.objects.create(
            post=post,
            social_account=account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="media-1",
            platform_extra={"post_type": "story"},
        )

    def test_a_story_never_gets_a_first_comment(self):
        with patch("apps.publisher.engine._post_first_comment_task") as task:
            PublishEngine()._maybe_schedule_first_comment(self.platform_post)

        task.assert_not_called()

    def test_a_feed_post_on_the_same_account_still_does(self):
        self.platform_post.platform_extra = {}
        self.platform_post.save(update_fields=["platform_extra"])

        with patch("apps.publisher.engine._post_first_comment_task") as task:
            PublishEngine()._maybe_schedule_first_comment(self.platform_post)

        task.assert_called_once()
