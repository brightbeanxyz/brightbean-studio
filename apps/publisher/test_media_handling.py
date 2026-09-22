"""Tests for how the publish engine gets media to a provider.

The engine used to download every attachment to local disk once per platform,
in parallel threads — even for the providers that publish from a hosted URL and
never open the file. On a 512 MB dyno that was the difference between publishing
and an out-of-memory kill, so both behaviours are pinned here.
"""

import os
import threading
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.publisher.engine import PublishEngine, _SharedMediaCache
from apps.publisher.models import PublishLog
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers.types import AuthType, PostType, PublishResult


def _attachment(asset_id, *, media_type="image", filename="a.jpg", duration=0):
    asset = MagicMock()
    asset.id = asset_id
    asset.media_type = media_type
    asset.filename = filename
    asset.duration = duration
    asset.file.url = f"https://cdn.example/{filename}"
    pm = MagicMock()
    pm.media_asset = asset
    return pm


def _dispatch_mocks(platform, *, needs_local_media, attachments=(), supported=(PostType.TEXT,)):
    account = MagicMock()
    account.platform = platform
    account.account_platform_id = "acct-1"
    account.token_expires_at = None
    account.oauth_access_token = "tok"
    account.account_name = "Test Account"

    platform_post = MagicMock()
    platform_post.social_account = account
    platform_post.post.media_attachments.select_related.return_value.order_by.return_value = list(attachments)
    platform_post.post.tags = []
    platform_post.effective_caption = "hello"
    platform_post.effective_title = None
    platform_post.effective_first_comment = None
    platform_post.platform_extra = {}

    provider = MagicMock()
    provider.auth_type = AuthType.OAUTH2
    provider.supported_post_types = list(supported)
    provider.needs_local_media = needs_local_media
    provider.publish_is_async = False
    provider.publish_post.return_value = PublishResult(platform_post_id="p1", url=None, extra={})
    return PublishEngine(), platform_post, provider


class UrlOnlyProvidersSkipDownloadTest(SimpleTestCase):
    """Instagram, Threads, Facebook et al. never read ``media_files``."""

    @patch("apps.publisher.engine.download_to_path")
    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_no_bytes_are_downloaded(self, _creds, get_provider, download):
        engine, platform_post, provider = _dispatch_mocks(
            "instagram", needs_local_media=False, attachments=[_attachment("a1")]
        )
        get_provider.return_value = provider

        engine._dispatch_to_provider(platform_post)

        download.assert_not_called()
        _token, content = provider.publish_post.call_args.args
        assert content.media_files == []
        assert content.media_urls == ["https://cdn.example/a.jpg"]

    @patch("apps.publisher.engine.download_to_path")
    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_carousel_survives_the_skipped_download(self, _creds, get_provider, download):
        """Regression: post type was derived from len(media_files).

        With the download skipped that count is zero, which silently demoted
        every multi-image Instagram post from a carousel to a single image.
        """
        engine, platform_post, provider = _dispatch_mocks(
            "instagram",
            needs_local_media=False,
            attachments=[_attachment("a1"), _attachment("a2", filename="b.jpg")],
        )
        get_provider.return_value = provider

        engine._dispatch_to_provider(platform_post)

        download.assert_not_called()
        _token, content = provider.publish_post.call_args.args
        assert content.post_type is PostType.CAROUSEL

    @patch("apps.publisher.engine.download_to_path")
    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_media_type_still_drives_post_type(self, _creds, get_provider, download):
        """first_media_type is also collected in that loop — a single image
        post must not fall through to TEXT."""
        engine, platform_post, provider = _dispatch_mocks(
            "instagram", needs_local_media=False, attachments=[_attachment("a1")]
        )
        get_provider.return_value = provider

        engine._dispatch_to_provider(platform_post)

        _token, content = provider.publish_post.call_args.args
        assert content.post_type is PostType.IMAGE

    @patch("apps.publisher.engine.download_to_path")
    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_video_duration_still_reaches_the_provider(self, _creds, get_provider, download):
        engine, platform_post, provider = _dispatch_mocks(
            "instagram",
            needs_local_media=False,
            attachments=[_attachment("a1", media_type="video", filename="v.mp4", duration=42.5)],
        )
        get_provider.return_value = provider

        engine._dispatch_to_provider(platform_post)

        _token, content = provider.publish_post.call_args.args
        assert content.video_duration_sec == 42.5


class LocalMediaProvidersStillDownloadTest(SimpleTestCase):
    @patch("apps.publisher.engine.download_to_path")
    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_file_path_is_handed_to_the_provider(self, _creds, get_provider, download):
        engine, platform_post, provider = _dispatch_mocks(
            "tiktok",
            needs_local_media=True,
            attachments=[_attachment("a1", media_type="video", filename="v.mp4")],
            supported=(PostType.VIDEO,),
        )
        get_provider.return_value = provider

        engine._dispatch_to_provider(platform_post)

        download.assert_called_once()
        _token, content = provider.publish_post.call_args.args
        assert len(content.media_files) == 1
        # Cleaned up on the way out — nothing may outlive the publish.
        assert not os.path.exists(content.media_files[0])


class SharedMediaCacheTest(SimpleTestCase):
    """One download per asset per post, however many platforms want it."""

    @patch("apps.publisher.engine.download_to_path")
    def test_different_assets_do_not_serialize_on_one_lock(self, download):
        """Per-asset locks: one wedged download must not block the other platforms.

        A single cache-wide lock held across the network call meant every
        publish thread in the group waited on whichever download went first —
        and a hung one stalled the executor's join, and with it the worker.
        """
        cache = _SharedMediaCache()
        first = _attachment("slow", filename="a.mp4").media_asset
        second = _attachment("quick", filename="b.mp4").media_asset
        released = threading.Event()
        started = threading.Event()

        def _blocking(file_field, dest):
            started.set()
            released.wait(5)

        download.side_effect = _blocking
        blocker = threading.Thread(target=cache.path_for, args=(first,), daemon=True)
        blocker.start()
        assert started.wait(5), "first download never started"

        try:
            download.side_effect = None
            # Would time out if this waited on the blocked download's lock.
            assert cache.path_for(second)
        finally:
            released.set()
            blocker.join(5)
            cache.cleanup()

    @patch("apps.publisher.engine.download_to_path")
    def test_repeated_requests_download_once(self, download):
        cache = _SharedMediaCache()
        asset = _attachment("a1", media_type="video", filename="v.mp4").media_asset

        first = cache.path_for(asset)
        second = cache.path_for(asset)

        assert first == second
        download.assert_called_once()
        cache.cleanup()
        assert not os.path.exists(first)

    @patch("apps.publisher.engine.download_to_path", side_effect=RuntimeError("storage down"))
    def test_a_failed_download_leaves_no_temp_file_behind(self, _download):
        cache = _SharedMediaCache()
        asset = _attachment("a1").media_asset

        with self.assertRaises(RuntimeError):
            cache.path_for(asset)

        assert cache._entries["a1"].path is None


class RetryBackoffIsHonouredTest(TestCase):
    """The due query used to ignore next_retry_at, so backoff never happened.

    A row parked on a 30-minute backoff came straight back on the next 15-second
    tick: four attempts inside a minute instead of across half an hour — and for
    a video platform, four uploads of the same file.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-1",
            account_name="acct",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        past = timezone.now() - timedelta(minutes=5)
        self.post = Post.objects.create(workspace=self.workspace, caption="hi", scheduled_at=past)
        self.pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.SCHEDULED,
            scheduled_at=past,
        )

    def _due_ids(self):
        return [pp.id for pp in PublishEngine()._get_due_platform_posts()]

    def test_row_parked_on_backoff_is_not_due(self):
        self.pp.retry_count = 1
        self.pp.next_retry_at = timezone.now() + timedelta(minutes=30)
        self.pp.save()

        assert self._due_ids() == []

    def test_row_becomes_due_once_the_backoff_elapses(self):
        self.pp.retry_count = 1
        self.pp.next_retry_at = timezone.now() - timedelta(seconds=1)
        self.pp.save()

        assert self._due_ids() == [self.pp.id]

    def test_a_never_retried_row_is_unaffected(self):
        """The gate must key on retry_count, not on a stale next_retry_at."""
        self.pp.retry_count = 0
        self.pp.next_retry_at = timezone.now() + timedelta(minutes=30)
        self.pp.save()

        assert self._due_ids() == [self.pp.id]


class RescheduleResetsTheRetryBudgetTest(TestCase):
    """A deliberate re-schedule must not inherit the previous attempt's backoff.

    A post that exhausted its retries keeps ``retry_count == MAX_RETRIES``. Put
    straight back to ``scheduled``, it would be failed permanently on its very
    first attempt — the user's retry would get no budget at all.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-1",
            account_name="acct",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi")
        self.pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.FAILED,
            retry_count=3,
            next_retry_at=timezone.now() + timedelta(minutes=30),
            publish_error="Publishing kept failing.",
        )

    def test_transition_to_scheduled_clears_the_backoff(self):
        self.pp.transition_to("scheduled")

        assert self.pp.retry_count == 0
        assert self.pp.next_retry_at is None
        assert self.pp.publish_error == ""

    def test_the_reset_is_actually_persisted(self):
        """update_fields at the call sites must include the reset columns."""
        self.pp.transition_to("scheduled")
        self.pp.save(
            update_fields=["status", "published_at", "retry_count", "next_retry_at", "publish_error", "updated_at"]
        )
        self.pp.refresh_from_db()

        assert self.pp.retry_count == 0
        assert self.pp.next_retry_at is None

    def test_other_transitions_leave_the_budget_alone(self):
        self.pp.transition_to("draft")

        assert self.pp.retry_count == 3


class AsyncPublishHoldsThePublishingStatusTest(TransactionTestCase):
    """Regression: an async publish must LEAVE the row in ``publishing``.

    ``_publish_post_group`` flips the status with a queryset ``.update()``, which
    does not refresh the in-memory objects — they still read ``scheduled``. The
    async branch's ``save()`` wrote that stale value back, so every TikTok
    publish left the row due again and the next 15s tick re-uploaded the video.
    On a live account that is an unbounded stream of duplicate posts.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-1",
            account_name="acct",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        past = timezone.now() - timedelta(minutes=5)
        self.post = Post.objects.create(workspace=self.workspace, caption="hi", scheduled_at=past)
        self.pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.SCHEDULED,
            scheduled_at=past,
        )

    def _publish(self, async_publish):
        with patch.object(
            PublishEngine,
            "_dispatch_to_provider",
            return_value={
                "success": True,
                "platform_post_id": "v_pub_file~abc",
                "url": None,
                "response": {},
                "async_publish": async_publish,
            },
        ) as dispatch:
            PublishEngine()._publish_post_group(self.post, [self.pp])
        self.pp.refresh_from_db()
        return dispatch

    def test_row_stays_publishing_and_is_not_due_again(self):
        self._publish(async_publish=True)

        assert self.pp.status == PlatformPost.Status.PUBLISHING
        assert self.pp.platform_post_id == "v_pub_file~abc"
        assert self.pp.id not in {p.id for p in PublishEngine()._get_due_platform_posts()}

    def test_a_second_cycle_does_not_republish(self):
        """The whole point: no duplicate upload on the next tick."""
        self._publish(async_publish=True)

        with patch.object(PublishEngine, "_dispatch_to_provider") as dispatch:
            PublishEngine().poll_and_publish()

        dispatch.assert_not_called()

    def test_a_synchronous_publish_still_completes(self):
        self._publish(async_publish=False)

        assert self.pp.status == PlatformPost.Status.PUBLISHED
        assert self.pp.published_at is not None

    def test_the_attempt_number_survives_the_retry_reset(self):
        """retry_count is zeroed on success; the log must still record attempt 4."""
        PlatformPost.objects.filter(pk=self.pp.pk).update(retry_count=3)
        self.pp.refresh_from_db()

        self._publish(async_publish=True)

        log = PublishLog.objects.get(platform_post=self.pp)
        assert log.attempt_number == 4
        assert self.pp.retry_count == 0
