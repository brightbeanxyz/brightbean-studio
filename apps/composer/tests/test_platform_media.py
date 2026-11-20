"""Per-channel media: a platform post can publish its own images.

Covers saving the choice from the composer, the "channel has its own image"
check before scheduling, and which attachments the publisher picks.
"""

from django.core.files.base import ContentFile
from django.urls import reverse

from apps.composer.models import PlatformPost, Post, PostMedia
from apps.composer.views import _parse_override_media_ids
from apps.media_library.models import MediaAsset
from apps.publisher.engine import PublishEngine
from apps.social_accounts.models import SocialAccount

from .test_unsplash import ComposerTestCase


def _image(workspace, name):
    asset = MediaAsset.objects.create(
        organization=workspace.organization,
        workspace=workspace,
        filename=name,
        media_type=MediaAsset.MediaType.IMAGE,
        file_size=1,
        processing_status=MediaAsset.ProcessingStatus.COMPLETED,
    )
    asset.file.save(name, ContentFile(b"x"), save=True)
    return asset


class PlatformMediaTests(ComposerTestCase):
    def setUp(self):
        super().setUp()
        self.instagram = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="instagram",
            account_platform_id="ig-1",
            account_name="IG",
            connection_status="connected",
        )
        self.facebook = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="fb-1",
            account_name="FB",
            connection_status="connected",
        )
        self.shared = _image(self.workspace, "shared.jpg")
        self.square = _image(self.workspace, "square.jpg")
        self.save_url = reverse("composer:save_post", kwargs={"workspace_id": self.workspace.id})

    def _save(self, **extra):
        data = {
            "action": "save_draft",
            "title": "t",
            "caption": "body",
            "selected_accounts": f"{self.instagram.id},{self.facebook.id}",
        }
        data.update(extra)
        response = self.client.post(self.save_url, data=data)
        self.assertIn(response.status_code, (200, 204, 302))
        return Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()

    def test_save_stores_media_for_one_channel_only(self):
        post = self._save(**{f"override_media_{self.instagram.id}": str(self.square.id)})
        ig = PlatformPost.objects.get(post=post, social_account=self.instagram)
        fb = PlatformPost.objects.get(post=post, social_account=self.facebook)
        self.assertEqual(ig.platform_specific_media, [str(self.square.id)])
        self.assertIsNone(fb.platform_specific_media)

    def test_empty_field_clears_the_choice(self):
        post = self._save(**{f"override_media_{self.instagram.id}": str(self.square.id)})
        self.client.post(
            reverse("composer:save_post_edit", kwargs={"workspace_id": self.workspace.id, "post_id": post.id}),
            data={
                "action": "save_draft",
                "title": "t",
                "caption": "body",
                "selected_accounts": str(self.instagram.id),
                f"override_media_{self.instagram.id}": "",
            },
        )
        ig = PlatformPost.objects.get(post=post, social_account=self.instagram)
        self.assertIsNone(ig.platform_specific_media)

    def test_absent_field_keeps_the_choice(self):
        post = self._save(**{f"override_media_{self.instagram.id}": str(self.square.id)})
        self.client.post(
            reverse("composer:save_post_edit", kwargs={"workspace_id": self.workspace.id, "post_id": post.id}),
            data={
                "action": "save_draft",
                "title": "t",
                "caption": "body",
                "selected_accounts": str(self.instagram.id),
            },
        )
        ig = PlatformPost.objects.get(post=post, social_account=self.instagram)
        self.assertEqual(ig.platform_specific_media, [str(self.square.id)])

    def test_foreign_and_malformed_ids_are_dropped(self):
        other_org_ws = type(self.workspace).objects.create(
            organization=type(self.org).objects.create(name="Other"), name="Other WS"
        )
        foreign = _image(other_org_ws, "foreign.jpg")
        post = self._save(
            **{f"override_media_{self.instagram.id}": f"{foreign.id},not-a-uuid,{self.square.id}"}
        )
        ig = PlatformPost.objects.get(post=post, social_account=self.instagram)
        self.assertEqual(ig.platform_specific_media, [str(self.square.id)])

    def test_parse_returns_none_when_field_missing(self):
        class Req:
            POST = {}

        self.assertIsNone(_parse_override_media_ids(Req, "abc"))

    def test_publisher_uses_channel_media_instead_of_shared(self):
        post = self._save()
        PostMedia.objects.create(post=post, media_asset=self.shared, position=0, alt_text="alt")
        ig = PlatformPost.objects.get(post=post, social_account=self.instagram)
        fb = PlatformPost.objects.get(post=post, social_account=self.facebook)
        ig.platform_specific_media = [str(self.square.id)]
        ig.save()

        ig_media = PublishEngine._effective_attachments(ig)
        fb_media = PublishEngine._effective_attachments(fb)

        self.assertEqual([pm.media_asset_id for pm in ig_media], [self.square.id])
        self.assertEqual([pm.media_asset_id for pm in fb_media], [self.shared.id])

    def test_publisher_falls_back_when_chosen_asset_is_gone(self):
        post = self._save()
        PostMedia.objects.create(post=post, media_asset=self.shared, position=0)
        ig = PlatformPost.objects.get(post=post, social_account=self.instagram)
        ig.platform_specific_media = ["00000000-0000-0000-0000-000000000000"]
        ig.save()

        self.assertEqual(
            [pm.media_asset_id for pm in PublishEngine._effective_attachments(ig)],
            [self.shared.id],
        )

    def test_schedule_accepts_instagram_with_only_channel_media(self):
        data = {
            "action": "schedule",
            "title": "t",
            "caption": "body",
            "selected_accounts": str(self.instagram.id),
            "scheduled_date": "2030-01-01",
            "scheduled_time": "09:00",
        }
        without = self.client.post(self.save_url, data=data)
        self.assertEqual(without.status_code, 400)
        self.assertIn("media", without.json().get("errors", {}))

        data[f"override_media_{self.instagram.id}"] = str(self.square.id)
        with_media = self.client.post(self.save_url, data=data)
        self.assertNotEqual(with_media.status_code, 400, with_media.content)

    def test_create_post_service_stores_channel_media(self):
        from apps.composer.services import create_post

        post = create_post(
            workspace=self.workspace,
            social_account=self.instagram,
            caption="c",
            media_asset_ids=[self.shared.id],
            status="draft",
            platform_overrides={self.instagram.id: {"media_asset_ids": [self.square.id]}},
        )
        pp = post.platform_posts.get()
        self.assertEqual(pp.platform_specific_media, [str(self.square.id)])
        self.assertEqual([pm.media_asset_id for pm in post.media_attachments.all()], [self.shared.id])

    def test_create_post_service_rejects_foreign_channel_media(self):
        from apps.composer.services import create_post

        other = type(self.workspace).objects.create(
            organization=type(self.org).objects.create(name="Other"), name="Other WS"
        )
        foreign = _image(other, "foreign.jpg")
        with self.assertRaises(ValueError):
            create_post(
                workspace=self.workspace,
                social_account=self.instagram,
                caption="c",
                status="draft",
                platform_overrides={self.instagram.id: {"media_asset_ids": [foreign.id]}},
            )
