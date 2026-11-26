"""Per-platform media: one post, different images/videos per account.

A cross-post can give an account its own media (``PlatformPost.platform_specific_media``),
e.g. a 4:5 image for Instagram while Facebook publishes the post's 1:1. These
tests pin every place that decides what a platform publishes: the stored value,
the composer save, the scheduling gates, the preview and the publisher.
"""

import json
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post, PostMedia, normalize_media_ids, resolve_media_assets
from apps.composer.services import (
    media_change_blocker,
    platform_post_media_types,
    require_publishable,
)
from apps.composer.views import _validate_required_media
from apps.media_library.models import MediaAsset
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.publisher.engine import PublishEngine
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers.types import AuthType, PostType, PublishResult


class PlatformMediaTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org = Organization.objects.create(name="Test Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="Test Workspace")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace,
            workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
        )
        self.client.force_login(self.user)

        self.facebook = self._account("facebook", "fb-1", "Page")
        self.instagram = self._account("instagram", "ig-1", "Insta")
        self.tiktok = self._account("tiktok", "tt-1", "Creator")

        self.post = Post.objects.create(workspace=self.workspace, author=self.user, caption="hello")
        self.square = self._asset("square.jpg", width=1080, height=1080)
        PostMedia.objects.create(post=self.post, media_asset=self.square, position=0)
        self.portrait = self._asset("portrait.jpg", width=1080, height=1350)
        self.fb_pp = PlatformPost.objects.create(post=self.post, social_account=self.facebook)
        self.ig_pp = PlatformPost.objects.create(post=self.post, social_account=self.instagram)

    def _account(self, platform, platform_id, name):
        return SocialAccount.objects.create(
            workspace=self.workspace,
            platform=platform,
            account_platform_id=platform_id,
            account_name=name,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

    def _asset(self, filename, *, media_type=MediaAsset.MediaType.IMAGE, workspace=None, shared=False, **dims):
        return MediaAsset.objects.create(
            organization=self.org,
            workspace=None if shared else (workspace or self.workspace),
            uploaded_by=self.user,
            file=f"test/{filename}",
            filename=filename,
            media_type=media_type,
            mime_type="video/mp4" if media_type == MediaAsset.MediaType.VIDEO else "image/jpeg",
            **dims,
        )


class MediaIdHelpersTests(PlatformMediaTestBase):
    def test_normalize_keeps_order_drops_junk_and_duplicates(self):
        a, b = str(self.square.id), str(self.portrait.id)
        assert normalize_media_ids([b, "not-a-uuid", a, b, None, 42]) == [b, a]
        assert normalize_media_ids(f" {a} ,{b},,") == [a, b]
        assert normalize_media_ids(None) == []
        assert normalize_media_ids({"id": a}) == []

    def test_resolve_limits_to_workspace_and_shared_library(self):
        other_ws = Workspace.objects.create(organization=self.org, name="Other")
        foreign = self._asset("foreign.jpg", workspace=other_ws)
        shared = self._asset("shared.jpg", shared=True)
        other_org = Organization.objects.create(name="Other Org")
        other_org_asset = MediaAsset.objects.create(
            organization=other_org,
            workspace=Workspace.objects.create(organization=other_org, name="X"),
            file="test/x.jpg",
            filename="x.jpg",
            media_type="image",
        )
        ids = [self.portrait.id, foreign.id, shared.id, other_org_asset.id]
        assert resolve_media_assets(ids, self.workspace) == [self.portrait, shared]


class EffectiveMediaTests(PlatformMediaTestBase):
    def test_no_override_publishes_post_media(self):
        assert self.ig_pp.has_media_override is False
        assert self.ig_pp.effective_media_assets() == [self.square]

    def test_override_replaces_post_media_in_order(self):
        second = self._asset("second.jpg")
        self.ig_pp.platform_specific_media = [str(second.id), str(self.portrait.id)]
        self.ig_pp.save()
        assert self.ig_pp.effective_media_assets() == [second, self.portrait]
        # The sibling keeps the post's media.
        assert self.fb_pp.effective_media_assets() == [self.square]

    def test_empty_or_malformed_override_falls_back_to_post_media(self):
        for stored in ([], None, ["garbage"], "oops"):
            self.ig_pp.platform_specific_media = stored
            assert self.ig_pp.effective_media_assets() == [self.square], stored


class ComposerSaveTests(PlatformMediaTestBase):
    def setUp(self):
        super().setUp()
        self.save_url = reverse(
            "composer:save_post_edit",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id},
        )

    def _payload(self, **extra):
        payload = {
            "action": "save_draft",
            "title": "",
            "caption": "hello",
            "tags": "",
            "selected_accounts": f"{self.facebook.id},{self.instagram.id}",
        }
        payload.update(extra)
        return payload

    def test_save_stores_override_for_one_account_only(self):
        other_ws = Workspace.objects.create(organization=self.org, name="Other")
        foreign = self._asset("foreign.jpg", workspace=other_ws)
        response = self.client.post(
            self.save_url,
            self._payload(
                **{
                    f"override_media_panel_{self.facebook.id}": "1",
                    f"override_media_{self.facebook.id}": "",
                    f"override_media_panel_{self.instagram.id}": "1",
                    f"override_media_{self.instagram.id}": f"{self.portrait.id},{foreign.id}",
                }
            ),
        )
        assert response.status_code in (200, 302), response.content[:300]
        self.ig_pp.refresh_from_db()
        self.fb_pp.refresh_from_db()
        # The other workspace's asset never reaches the row.
        assert self.ig_pp.platform_specific_media == [str(self.portrait.id)]
        assert self.fb_pp.platform_specific_media is None

    def test_empty_panel_clears_a_stored_override(self):
        self.ig_pp.platform_specific_media = [str(self.portrait.id)]
        self.ig_pp.save()
        self.client.post(
            self.save_url,
            self._payload(**{f"override_media_panel_{self.instagram.id}": "1"}),
        )
        self.ig_pp.refresh_from_db()
        assert self.ig_pp.platform_specific_media is None

    def test_save_without_the_panel_leaves_a_stored_override_alone(self):
        self.ig_pp.platform_specific_media = [str(self.portrait.id)]
        self.ig_pp.save()
        self.client.post(self.save_url, self._payload())
        self.ig_pp.refresh_from_db()
        assert self.ig_pp.platform_specific_media == [str(self.portrait.id)]

    def test_reopened_post_carries_its_saved_overrides(self):
        """Regression: the composer used to open every override panel empty, so
        saving a reopened post silently erased its per-platform caption."""
        self.ig_pp.platform_specific_caption = "Instagram-only caption"
        self.ig_pp.platform_specific_media = [str(self.portrait.id)]
        self.ig_pp.save()
        response = self.client.get(
            reverse("composer:compose_edit", kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id})
        )
        assert response.status_code == 200
        overrides = response.context["platform_overrides"]
        assert set(overrides) == {str(self.instagram.id)}
        assert overrides[str(self.instagram.id)]["caption"] == "Instagram-only caption"
        assert [m["id"] for m in overrides[str(self.instagram.id)]["media"]] == [str(self.portrait.id)]
        assert '<script id="composer-platform-overrides" type="application/json">' in response.content.decode()


class SchedulingGateTests(PlatformMediaTestBase):
    """TikTok only publishes video: its gate must look at TikTok's own media."""

    def setUp(self):
        super().setUp()
        self.video = self._asset("clip.mp4", media_type=MediaAsset.MediaType.VIDEO, width=1080, height=1920)
        self.tt_pp = PlatformPost.objects.create(post=self.post, social_account=self.tiktok)

    def test_override_video_satisfies_video_only_platform(self):
        with self.assertRaises(ValueError):
            require_publishable(self.tt_pp)  # the post itself only has an image
        self.tt_pp.platform_specific_media = [str(self.video.id)]
        self.tt_pp.save()
        assert platform_post_media_types(self.tt_pp) == {"video"}
        require_publishable(self.tt_pp)

    def test_override_image_blocks_video_only_platform_even_with_post_video(self):
        PostMedia.objects.create(post=self.post, media_asset=self.video, position=1)
        require_publishable(self.tt_pp)
        self.tt_pp.platform_specific_media = [str(self.portrait.id)]
        self.tt_pp.save()
        with self.assertRaises(ValueError):
            require_publishable(self.tt_pp)
        # The bulk path passes the post's answer; the override still wins.
        with self.assertRaises(ValueError):
            require_publishable(self.tt_pp, media_types={"image", "video"})

    def test_removing_post_media_does_not_strand_a_row_with_its_own_media(self):
        self.tt_pp.platform_specific_media = [str(self.video.id)]
        self.tt_pp.status = PlatformPost.Status.SCHEDULED
        self.tt_pp.save()
        assert media_change_blocker(self.post, media_types_after=set()) == ""

    def test_composer_schedule_check_reads_the_submitted_override(self):
        factory = RequestFactory()

        def check(**fields):
            request = factory.post(
                "/",
                {"action": "schedule", "selected_accounts": str(self.tiktok.id), **fields},
            )
            request.session = {}
            return _validate_required_media(request, self.post, self.workspace, "schedule")

        assert check() is not None  # image-only post, no override
        assert (
            check(
                **{
                    f"override_media_panel_{self.tiktok.id}": "1",
                    f"override_media_{self.tiktok.id}": str(self.video.id),
                }
            )
            is None
        )
        # A stored override counts when the form has no panel for it.
        self.tt_pp.platform_specific_media = [str(self.video.id)]
        self.tt_pp.save()
        assert check() is None


class PreviewTests(PlatformMediaTestBase):
    def test_each_card_shows_its_own_media(self):
        response = self.client.post(
            reverse("composer:preview", kwargs={"workspace_id": self.workspace.id}),
            {
                "caption": "hello",
                "selected_accounts": f"{self.facebook.id},{self.instagram.id}",
                "_autosave_post_id": str(self.post.id),
                f"override_media_panel_{self.instagram.id}": "1",
                f"override_media_{self.instagram.id}": str(self.portrait.id),
            },
        )
        assert response.status_code == 200
        previews = {str(p["account"].id): p for p in response.context["previews"]}
        fb, ig = previews[str(self.facebook.id)], previews[str(self.instagram.id)]
        assert [m["filename"] for m in fb["media_items"]] == ["square.jpg"]
        assert [m["filename"] for m in ig["media_items"]] == ["portrait.jpg"]
        assert ig["has_media_override"] and not fb["has_media_override"]
        # Instagram shows the 4:5 image at 4:5 rather than squared off.
        assert ig["media_items"][0]["ig_aspect"] == "0.8000"
        assert "Own media" in response.content.decode()


class OverrideEndpointsTests(PlatformMediaTestBase):
    def test_picker_lists_images_and_videos(self):
        self._asset("clip.mp4", media_type=MediaAsset.MediaType.VIDEO)
        response = self.client.get(
            reverse("composer:override_media_picker", kwargs={"workspace_id": self.workspace.id})
        )
        body = response.content.decode()
        assert response.status_code == 200
        assert "portrait.jpg" in body and "clip.mp4" in body
        assert "override-media-selected" in body

    def test_upload_rejects_non_media_files(self):
        response = self.client.post(
            reverse("composer:override_media_upload", kwargs={"workspace_id": self.workspace.id}),
            {"file": SimpleUploadedFile("notes.txt", b"just some text", content_type="image/jpeg")},
        )
        assert response.status_code == 400
        assert "image and video" in response.json()["error"]


class PublisherTests(PlatformMediaTestBase):
    """The publisher hands each platform its own media."""

    def _dispatch(self, platform_post):
        provider = MagicMock()
        provider.auth_type = AuthType.OAUTH2
        provider.supported_post_types = [PostType.TEXT, PostType.IMAGE, PostType.CAROUSEL]
        provider.needs_local_media = False
        provider.publish_is_async = False
        provider.publish_post.return_value = PublishResult(platform_post_id="p1", url=None, extra={})
        with (
            patch("apps.publisher.engine.get_provider", return_value=provider),
            patch("apps.publisher.engine._resolve_publish_credentials", return_value={}),
        ):
            PublishEngine()._dispatch_to_provider(platform_post)
        _token, content = provider.publish_post.call_args.args
        return content

    def test_each_platform_publishes_its_own_media(self):
        self.ig_pp.platform_specific_media = [str(self.portrait.id)]
        self.ig_pp.save()
        ig_content = self._dispatch(PlatformPost.objects.select_related("social_account", "post").get(pk=self.ig_pp.pk))
        fb_content = self._dispatch(PlatformPost.objects.select_related("social_account", "post").get(pk=self.fb_pp.pk))
        assert [u.rsplit("/", 1)[-1] for u in ig_content.media_urls] == ["portrait.jpg"]
        assert [u.rsplit("/", 1)[-1] for u in fb_content.media_urls] == ["square.jpg"]

    def test_override_of_several_images_publishes_a_carousel(self):
        second = self._asset("second.jpg", width=1080, height=1350)
        self.ig_pp.platform_specific_media = [str(self.portrait.id), str(second.id)]
        self.ig_pp.save()
        content = self._dispatch(PlatformPost.objects.select_related("social_account", "post").get(pk=self.ig_pp.pk))
        assert [u.rsplit("/", 1)[-1] for u in content.media_urls] == ["portrait.jpg", "second.jpg"]
        assert content.post_type == PostType.CAROUSEL


class VersionSnapshotTests(PlatformMediaTestBase):
    def test_snapshot_records_media_override(self):
        from apps.composer.views import _save_version

        self.ig_pp.platform_specific_media = [str(self.portrait.id)]
        self.ig_pp.save()
        _save_version(self.post, self.user)
        snapshot = self.post.versions.latest("version_number").snapshot
        by_account = {row["social_account_id"]: row for row in snapshot["platform_posts"]}
        assert by_account[str(self.instagram.id)]["media_override"] == [str(self.portrait.id)]
        assert by_account[str(self.facebook.id)]["media_override"] == []
        json.dumps(snapshot)  # stays JSON-serialisable
