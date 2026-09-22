"""Tests for the Publishing Engine (T-1A.3)."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.publisher.engine import MAX_RETRIES, RETRY_BACKOFF, PublishEngine, _resolve_publish_credentials
from apps.publisher.models import PublishLog, RateLimitState
from providers.types import AuthType, PostType, PublishResult


class RateLimitStateModelTest(TestCase):
    """Test RateLimitState model logic."""

    def test_is_rate_limited_when_zero_remaining_and_window_active(self):
        state = RateLimitState()
        state.requests_remaining = 0
        state.window_resets_at = timezone.now() + timedelta(minutes=5)
        self.assertTrue(state.is_rate_limited)

    def test_is_not_rate_limited_when_zero_remaining_and_window_expired(self):
        state = RateLimitState()
        state.requests_remaining = 0
        state.window_resets_at = timezone.now() - timedelta(minutes=5)
        self.assertFalse(state.is_rate_limited)

    def test_is_not_rate_limited_with_remaining_requests(self):
        state = RateLimitState()
        state.requests_remaining = 50
        state.window_resets_at = timezone.now() + timedelta(minutes=5)
        self.assertFalse(state.is_rate_limited)

    def test_can_publish_when_unknown(self):
        state = RateLimitState()
        state.requests_remaining = -1
        self.assertTrue(state.can_publish)

    def test_can_publish_when_remaining(self):
        state = RateLimitState()
        state.requests_remaining = 10
        self.assertTrue(state.can_publish)

    def test_cannot_publish_when_rate_limited(self):
        state = RateLimitState()
        state.requests_remaining = 0
        state.window_resets_at = timezone.now() + timedelta(minutes=5)
        self.assertFalse(state.can_publish)


class PublishEngineTest(TestCase):
    """Test PublishEngine core logic."""

    def test_retry_backoff_schedule(self):
        """Verify retry backoff values match spec."""
        self.assertEqual(RETRY_BACKOFF, [60, 300, 1800])
        self.assertEqual(MAX_RETRIES, 3)

    def test_engine_instantiates(self):
        engine = PublishEngine()
        self.assertIsNotNone(engine)

    @patch("apps.publisher.engine.PlatformPost.objects")
    def test_get_due_platform_posts_filters_correctly(self, mock_objects):
        """Engine should query PlatformPosts with a Coalesce effective_at filter."""
        engine = PublishEngine()
        mock_qs = MagicMock()
        mock_objects.filter.return_value = mock_qs
        mock_qs.annotate.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__getitem__ = MagicMock(return_value=[])

        engine._get_due_platform_posts()

        # First filter: editorial status (now lives on PlatformPost itself)
        first_call = mock_objects.filter.call_args_list[0]
        self.assertIn("status", first_call.kwargs)
        # Second filter (on annotated qs): effective_at__lte
        second_call = mock_qs.filter.call_args_list[0]
        self.assertIn("effective_at__lte", second_call.kwargs)


class PublishLogModelTest(TestCase):
    """Test PublishLog model."""

    def test_str_representation(self):
        log = PublishLog()
        log.attempt_number = 2
        log.status_code = 200
        s = str(log)
        self.assertIn("2", s)
        self.assertIn("200", s)


def _build_dispatch_mocks(platform: str, account_platform_id: str, platform_extra: dict | None = None):
    """Build the minimal mocks needed to exercise _dispatch_to_provider's
    extras-assembly without DB or filesystem side effects.

    Returns (engine, platform_post, mock_provider).
    """
    engine = PublishEngine()

    account = MagicMock()
    account.platform = platform
    account.account_platform_id = account_platform_id
    account.token_expires_at = None  # skip the OAuth refresh branch
    account.oauth_access_token = "tok"
    account.account_name = "Test Account"

    platform_post = MagicMock()
    platform_post.social_account = account
    platform_post.post.media_attachments.select_related.return_value.order_by.return_value = []
    platform_post.post.tags = []
    platform_post.effective_caption = "hello"
    platform_post.effective_title = None
    platform_post.effective_first_comment = None
    platform_post.platform_extra = platform_extra or {}

    mock_provider = MagicMock()
    mock_provider.auth_type = AuthType.OAUTH2
    mock_provider.supported_post_types = [PostType.TEXT]
    mock_provider.publish_post.return_value = PublishResult(
        platform_post_id="post-1",
        url="https://example.com/p/1",
        extra={},
    )
    return engine, platform_post, mock_provider


class DispatchExtraInjectionTest(SimpleTestCase):
    """Verify _dispatch_to_provider injects platform-specific extras."""

    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_injects_organization_author_for_linkedin_company(self, _mock_creds, mock_get_provider):
        engine, platform_post, mock_provider = _build_dispatch_mocks(
            platform="linkedin_company",
            account_platform_id="98765",
        )
        mock_get_provider.return_value = mock_provider

        engine._dispatch_to_provider(platform_post)

        mock_provider.publish_post.assert_called_once()
        _access_token, content = mock_provider.publish_post.call_args.args
        self.assertEqual(content.extra.get("author"), "urn:li:organization:98765")

    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_injects_ig_user_id_for_instagram(self, _mock_creds, mock_get_provider):
        engine, platform_post, mock_provider = _build_dispatch_mocks(
            platform="instagram",
            account_platform_id="17841400000000000",
        )
        mock_get_provider.return_value = mock_provider

        engine._dispatch_to_provider(platform_post)

        mock_provider.publish_post.assert_called_once()
        _access_token, content = mock_provider.publish_post.call_args.args
        self.assertEqual(content.extra.get("ig_user_id"), "17841400000000000")

    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_does_not_overwrite_explicit_author(self, _mock_creds, mock_get_provider):
        # When the caller has already set extra["author"], the engine must not
        # overwrite it — important for callers that pass a different URN.
        engine, platform_post, mock_provider = _build_dispatch_mocks(
            platform="linkedin_company",
            account_platform_id="98765",
            platform_extra={"author": "urn:li:organization:override"},
        )
        mock_get_provider.return_value = mock_provider

        engine._dispatch_to_provider(platform_post)

        _access_token, content = mock_provider.publish_post.call_args.args
        self.assertEqual(content.extra.get("author"), "urn:li:organization:override")

    @patch("apps.publisher.engine.get_provider")
    @patch("apps.publisher.engine._resolve_publish_credentials", return_value={})
    def test_does_not_inject_author_for_other_platforms(self, _mock_creds, mock_get_provider):
        # Sanity: the author-injection branch is scoped to linkedin_company only.
        engine, platform_post, mock_provider = _build_dispatch_mocks(
            platform="linkedin_personal",
            account_platform_id="11111",
        )
        mock_get_provider.return_value = mock_provider

        engine._dispatch_to_provider(platform_post)

        _access_token, content = mock_provider.publish_post.call_args.args
        self.assertNotIn("author", content.extra)


class ResolvePostTypeFacebookReelTest(SimpleTestCase):
    """The hop that turns a composer choice into a typed PostType.

    Both ends of the Facebook Reel path are covered elsewhere — the composer
    writing ``platform_extra["post_type"]``, and the provider turning
    ``PostType.REEL`` into Graph calls. This is the bridge between them.
    """

    def _resolve(self, **kwargs):
        kwargs.setdefault("platform", "facebook")
        kwargs.setdefault("platform_extra", {})
        kwargs.setdefault("media_count", 1)
        kwargs.setdefault("first_media_type", "video")
        return PublishEngine._resolve_post_type(**kwargs)

    def test_reel_hint_wins_over_the_media_type_fallback(self):
        self.assertEqual(self._resolve(platform_extra={"post_type": "reel"}), PostType.REEL)

    def test_explicit_video_hint_keeps_the_regular_page_upload(self):
        self.assertEqual(self._resolve(platform_extra={"post_type": "video"}), PostType.VIDEO)

    def test_a_lone_video_without_a_hint_is_a_regular_video(self):
        self.assertEqual(self._resolve(), PostType.VIDEO)

    def test_a_reel_hint_is_dropped_when_the_video_is_gone(self):
        """The hint is written on form submit; media changes persist on their own.

        Removing the video via the composer's htmx endpoint never revisits
        platform_extra, so a post could reach the publisher claiming REEL with
        nothing to upload — failing a post that would have published as text.
        """
        self.assertEqual(
            self._resolve(platform_extra={"post_type": "reel"}, media_count=0, first_media_type=None),
            PostType.TEXT,
        )

    def test_a_reel_hint_is_dropped_when_the_video_became_an_image(self):
        # One attachment still, so a count check alone would let this through
        # and send a JPEG to a Reels endpoint.
        self.assertEqual(
            self._resolve(platform_extra={"post_type": "reel"}, media_count=1, first_media_type="image"),
            PostType.IMAGE,
        )

    def test_a_reel_hint_is_dropped_when_a_second_attachment_arrived(self):
        self.assertEqual(
            self._resolve(platform_extra={"post_type": "reel"}, media_count=2, first_media_type="video"),
            PostType.VIDEO,
        )

    def test_a_video_hint_is_dropped_when_the_video_became_an_image(self):
        """_publish_video posts media_urls[0] to the video endpoint unchecked.

        A hint left over from a video that has since been replaced would send
        the image there, so the media has to be able to veto it.
        """
        self.assertEqual(
            self._resolve(platform_extra={"post_type": "video"}, media_count=1, first_media_type="image"),
            PostType.IMAGE,
        )

    def test_a_video_hint_is_dropped_when_the_media_is_gone(self):
        self.assertEqual(
            self._resolve(platform_extra={"post_type": "video"}, media_count=0, first_media_type=None),
            PostType.TEXT,
        )

    def test_a_hint_that_names_no_media_shape_is_left_alone(self):
        # TEXT/LINK/PIN say nothing about attachments, so the media must not veto them.
        self.assertEqual(
            self._resolve(platform_extra={"post_type": "link"}, media_count=0, first_media_type=None),
            PostType.LINK,
        )

    def test_an_unknown_hint_is_ignored_rather_than_raising(self):
        # PostType(hint) would raise ValueError inside the publish loop and
        # fail the post over a typo in stored JSON.
        self.assertEqual(self._resolve(platform_extra={"post_type": "shorts"}), PostType.VIDEO)


class ResolvePublishCredentialsTest(SimpleTestCase):
    @patch("apps.publisher.engine.resolve_platform_credentials", return_value={"client_id": "id"})
    def test_facebook_credentials_include_selected_page_id(self, _mock_resolve):
        account = MagicMock()
        account.platform = "facebook"
        account.account_platform_id = "page-1"
        account.workspace.organization_id = "org-1"

        credentials = _resolve_publish_credentials(account)

        self.assertEqual(credentials["page_id"], "page-1")

    @patch("apps.publisher.engine.resolve_platform_credentials", return_value={"client_id": "id"})
    def test_instagram_credentials_include_selected_ig_user_id(self, _mock_resolve):
        account = MagicMock()
        account.platform = "instagram"
        account.account_platform_id = "17841400000000000"
        account.workspace.organization_id = "org-1"

        credentials = _resolve_publish_credentials(account)

        self.assertEqual(credentials["ig_user_id"], "17841400000000000")

    @patch("apps.common.validators.is_safe_url", return_value=True)
    @patch("apps.publisher.engine.resolve_platform_credentials", return_value={})
    def test_bluesky_safe_pds_url_is_injected(self, _mock_resolve, _mock_is_safe_url):
        account = MagicMock()
        account.platform = "bluesky"
        account.instance_url = "https://pds.example.com"
        account.workspace.organization_id = "org-1"

        credentials = _resolve_publish_credentials(account)

        self.assertEqual(credentials["pds_url"], "https://pds.example.com")

    @patch("apps.common.validators.is_safe_url", return_value=False)
    @patch("apps.publisher.engine.resolve_platform_credentials", return_value={})
    def test_bluesky_unsafe_pds_url_is_rejected(self, _mock_resolve, _mock_is_safe_url):
        # The Bluesky pds_url sets the outbound host, so a URL that fails the SSRF
        # check must not reach the provider — parity with the Mastodon gate.
        account = MagicMock()
        account.platform = "bluesky"
        account.instance_url = "http://169.254.169.254"
        account.workspace.organization_id = "org-1"

        credentials = _resolve_publish_credentials(account)

        self.assertNotIn("pds_url", credentials)


class NonRetryableFailureTest(TestCase):
    """_publish_platform_post must honor the exception's ``retryable`` flag."""

    def setUp(self):
        from apps.composer.models import PlatformPost, Post
        from apps.organizations.models import Organization
        from apps.social_accounts.models import SocialAccount
        from apps.workspaces.models import Workspace

        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-1",
            account_name="janschmitz51",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi")
        self.platform_post = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHING,
        )

    def test_non_retryable_error_fails_immediately(self):
        from apps.composer.models import PlatformPost
        from providers.exceptions import PublishError

        engine = PublishEngine()
        error = PublishError("TikTok rejected the post: audit pending", platform="TikTok", retryable=False)
        with patch.object(PublishEngine, "_dispatch_to_provider", side_effect=error):
            result = engine._publish_platform_post(self.platform_post)

        self.assertFalse(result["success"])
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.status, PlatformPost.Status.FAILED)
        self.assertEqual(self.platform_post.retry_count, 0)
        self.assertIsNone(self.platform_post.next_retry_at)
        self.assertIn("audit pending", self.platform_post.publish_error)
        self.assertEqual(PublishLog.objects.filter(platform_post=self.platform_post).count(), 1)

    def test_retryable_error_schedules_backoff_retry(self):
        from apps.composer.models import PlatformPost
        from providers.exceptions import PublishError

        engine = PublishEngine()
        error = PublishError("transient", platform="TikTok")
        with patch.object(PublishEngine, "_dispatch_to_provider", side_effect=error):
            result = engine._publish_platform_post(self.platform_post)

        self.assertFalse(result["success"])
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.status, PlatformPost.Status.SCHEDULED)
        self.assertEqual(self.platform_post.retry_count, 1)
        self.assertIsNotNone(self.platform_post.next_retry_at)
        self.assertEqual(PublishLog.objects.filter(platform_post=self.platform_post).count(), 1)

    def test_quota_retry_waits_until_the_provider_reset(self):
        from apps.composer.models import PlatformPost
        from providers.exceptions import QuotaExceededError

        reset_at = timezone.now() + timedelta(hours=8)
        error = QuotaExceededError("daily quota spent", resets_at=reset_at, status_code=403)
        engine = PublishEngine()
        with patch.object(PublishEngine, "_dispatch_to_provider", side_effect=error):
            result = engine._publish_platform_post(self.platform_post)

        self.assertFalse(result["success"])
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.status, PlatformPost.Status.SCHEDULED)
        self.assertEqual(self.platform_post.next_retry_at, reset_at)
        self.assertEqual(self.platform_post.retry_count, 1)


class PublishedPostLeavesQueueTest(TestCase):
    """A successful publish drops the post's QueueEntry, freeing the slot."""

    def setUp(self):
        from apps.calendar.models import Queue, QueueEntry
        from apps.composer.models import PlatformPost, Post
        from apps.organizations.models import Organization
        from apps.social_accounts.models import SocialAccount
        from apps.workspaces.models import Workspace

        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-1",
            account_name="LI",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.queue = Queue.objects.create(workspace=self.workspace, name="Q", social_account=self.account)
        self.post = Post.objects.create(workspace=self.workspace, caption="hi")
        self.pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHING,
            scheduled_at=timezone.now() + timedelta(hours=1),
        )
        self.entry = QueueEntry.objects.create(
            queue=self.queue, post=self.post, position=0, assigned_slot_datetime=self.pp.scheduled_at
        )

    def test_publish_success_removes_queue_entry(self):
        from apps.calendar.models import QueueEntry
        from apps.composer.models import PlatformPost

        engine = PublishEngine()
        success = {"success": True, "platform_post_id": "x", "status_code": 200, "response": {}}
        with patch.object(PublishEngine, "_dispatch_to_provider", return_value=success):
            engine._publish_platform_post(self.pp)

        self.pp.refresh_from_db()
        self.assertEqual(self.pp.status, PlatformPost.Status.PUBLISHED)
        self.assertIsNotNone(self.pp.published_at)
        # The QueueEntry is gone (slot freed), but the PlatformPost remains.
        self.assertFalse(QueueEntry.objects.filter(id=self.entry.id).exists())

    def test_publish_success_stores_response_extra_on_platform_extra(self):
        from apps.composer.models import PlatformPost

        self.pp.platform_extra = {"post_type": "text"}
        self.pp.save(update_fields=["platform_extra"])

        engine = PublishEngine()
        success = {
            "success": True,
            "platform_post_id": "post-1",
            "status_code": 200,
            "response": {"id": "page-1_post-1", "tracking": {"source": "graph"}},
        }
        with patch.object(PublishEngine, "_dispatch_to_provider", return_value=success):
            engine._publish_platform_post(self.pp)

        self.pp.refresh_from_db()
        self.assertEqual(self.pp.status, PlatformPost.Status.PUBLISHED)
        self.assertEqual(self.pp.platform_post_id, "post-1")
        self.assertEqual(
            self.pp.platform_extra,
            {"post_type": "text", "id": "page-1_post-1", "tracking": {"source": "graph"}},
        )

    def test_publish_success_survives_queue_cleanup_failure(self):
        from apps.composer.models import PlatformPost

        engine = PublishEngine()
        success = {"success": True, "platform_post_id": "x", "status_code": 200, "response": {}}
        # The post is durably published; if the QueueEntry cleanup then fails it
        # must NOT fall through to a retry (which would re-dispatch and double-post).
        with (
            patch.object(PublishEngine, "_dispatch_to_provider", return_value=success),
            patch("apps.calendar.models.QueueEntry.objects") as mock_objects,
        ):
            mock_objects.filter.side_effect = Exception("db unavailable")
            engine._publish_platform_post(self.pp)

        self.pp.refresh_from_db()
        self.assertEqual(self.pp.status, PlatformPost.Status.PUBLISHED)
        self.assertEqual(self.pp.retry_count, 0)
        self.assertIsNone(self.pp.next_retry_at)


class PublishErrorIsNeverRawTest(TestCase):
    """publish_error renders in the composer and the calendar, so no path may
    write a provider response body into it."""

    def setUp(self):
        from apps.composer.models import PlatformPost, Post
        from apps.organizations.models import Organization
        from apps.social_accounts.models import SocialAccount
        from apps.workspaces.models import Workspace

        org = Organization.objects.create(name="Org")
        workspace = Workspace.objects.create(organization=org, name="WS")
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="instagram",
            account_platform_id="ig-1",
            account_name="IG",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        post = Post.objects.create(workspace=workspace, caption="hi")
        self.platform_post = PlatformPost.objects.create(
            post=post,
            social_account=account,
            status=PlatformPost.Status.SCHEDULED,
            scheduled_at=timezone.now(),
        )

    def test_a_rate_limited_account_does_not_show_an_internal_timestamp(self):
        from apps.publisher.models import RateLimitState
        from apps.social_accounts.error_messages import PUBLISH_RATE_LIMIT_MESSAGE

        RateLimitState.objects.create(
            social_account=self.platform_post.social_account,
            platform="instagram",
            requests_remaining=0,
            window_resets_at=timezone.now() + timedelta(hours=1),
        )

        PublishEngine()._publish_platform_post(self.platform_post)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.publish_error, PUBLISH_RATE_LIMIT_MESSAGE)

    def test_a_provider_reporting_failure_in_its_result_does_not_leak_the_body(self):
        """This branch has no exception to classify, so it always gets the
        generic sentence; the raw text lives in the PublishLog row."""
        from apps.social_accounts.error_messages import PUBLISH_GENERIC_MESSAGE

        raw = 'Instagram API error 400: {"error":{"fbtrace_id":"A4B_mFUQTXKx"}}'
        with patch.object(
            PublishEngine,
            "_dispatch_to_provider",
            return_value={"success": False, "error": raw, "status_code": 400},
        ):
            PublishEngine()._publish_platform_post(self.platform_post)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.publish_error, PUBLISH_GENERIC_MESSAGE)
        self.assertNotIn("fbtrace_id", self.platform_post.publish_error)
        self.assertIn("fbtrace_id", PublishLog.objects.get(platform_post=self.platform_post).error_message)

    def test_an_exhausted_retry_budget_stops_promising_a_retry(self):
        """The copy that got us here says "We'll retry shortly", which is true
        only while attempts remain."""
        from apps.composer.models import PlatformPost
        from apps.social_accounts.error_messages import (
            PUBLISH_EXHAUSTED_MESSAGE,
            PUBLISH_TEMPORARY_MESSAGE,
        )
        from providers.exceptions import APIError

        # Claimed into ``publishing`` first, because that is the only state
        # _publish_platform_post is ever entered in: both callers
        # (poll_and_publish's group fan-out and _process_retries) transition the
        # row before handing it over. _fail_permanently now refuses to settle a
        # row that is not mid-attempt — a ``scheduled`` row belongs to a pending
        # retry, and overwriting it would discard that retry and report a
        # failure that had not happened.
        self.platform_post.retry_count = MAX_RETRIES
        self.platform_post.status = PlatformPost.Status.PUBLISHING
        self.platform_post.save(update_fields=["retry_count", "status"])

        with patch.object(
            PublishEngine,
            "_dispatch_to_provider",
            side_effect=APIError("upstream down", status_code=503, platform="Instagram"),
        ):
            PublishEngine()._publish_platform_post(self.platform_post)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.status, PlatformPost.Status.FAILED)
        self.assertEqual(self.platform_post.publish_error, PUBLISH_EXHAUSTED_MESSAGE)
        self.assertNotEqual(self.platform_post.publish_error, PUBLISH_TEMPORARY_MESSAGE)
        self.assertNotIn("retry shortly", self.platform_post.publish_error)


class ResolvePostTypeFromMediaTypeTest(SimpleTestCase):
    """Post-type resolution driven by the *media* type rather than a hint.

    Distinct from ``ResolvePostTypeTest`` above, which covers the hint-driven
    Facebook Reel path. This one covers the rule that a lone Instagram video
    is a Reel even with no hint at all. Both classes were briefly named
    ``ResolvePostTypeTest``, which silently shadowed the ten tests above.
    """

    def _resolve(self, platform, first_media_type="video", media_count=1, extra=None):
        return PublishEngine._resolve_post_type(
            platform=platform,
            platform_extra=extra or {},
            media_count=media_count,
            first_media_type=first_media_type,
        )

    def test_a_lone_video_on_instagram_is_a_reel(self):
        """Instagram has no standalone feed video. Resolving one to VIDEO left
        each Instagram provider to translate it, and instagram_login did not —
        it published the .mp4 as image_url.
        """
        self.assertEqual(self._resolve("instagram"), PostType.REEL)
        self.assertEqual(self._resolve("instagram_login"), PostType.REEL)

    def test_a_lone_video_elsewhere_is_still_a_video(self):
        for platform in ("facebook", "threads", "tiktok", "youtube"):
            with self.subTest(platform=platform):
                self.assertEqual(self._resolve(platform), PostType.VIDEO)

    def test_a_lone_image_on_instagram_is_still_an_image(self):
        self.assertEqual(self._resolve("instagram_login", first_media_type="image"), PostType.IMAGE)

    def test_multi_media_still_wins_over_the_reel_rule(self):
        self.assertEqual(self._resolve("instagram_login", media_count=2), PostType.CAROUSEL)

    def test_an_explicit_hint_still_wins(self):
        self.assertEqual(
            self._resolve("instagram_login", extra={"post_type": "story"}),
            PostType.STORY,
        )


def _attachment(media_type: str, url: str, *, has_file: bool = True):
    """A stand-in media attachment for the dispatch loop.

    ``read`` returns b"" so the engine's temp-file download terminates at once.
    """
    pm = MagicMock()
    asset = pm.media_asset
    asset.media_type = media_type
    asset.filename = "asset.bin"
    asset.duration = 0
    asset.file = MagicMock() if has_file else None
    if has_file:
        asset.file.url = url
        asset.file.open.return_value.__enter__.return_value.read.return_value = b""
    return pm


class MediaTypePropagationTest(SimpleTestCase):
    """The engine holds the only trustworthy media type — the magic-byte sniff
    stored on the asset at upload. If it stops reaching PublishContent, every
    provider silently falls back to guessing from the URL suffix, which comes
    from the client-declared filename."""

    def _dispatch(self, attachments):
        engine, platform_post, mock_provider = _build_dispatch_mocks(
            platform="instagram_login",
            account_platform_id="ig-1",
        )
        platform_post.post.media_attachments.select_related.return_value.order_by.return_value = attachments
        with (
            patch("apps.publisher.engine.get_provider", return_value=mock_provider),
            patch("apps.publisher.engine._resolve_publish_credentials", return_value={}),
        ):
            engine._dispatch_to_provider(platform_post)
        _access_token, content = mock_provider.publish_post.call_args.args
        return content

    def test_the_assets_sniffed_type_reaches_the_provider(self):
        content = self._dispatch(
            [
                _attachment("image", "https://cdn.example/a.mp4?sig=x"),
                _attachment("video", "https://cdn.example/b.jpg?sig=x"),
            ]
        )

        self.assertEqual(content.media_types, ["image", "video"])
        # And the provider-facing question resolves against it, not the suffix.
        self.assertFalse(content.is_video(0))
        self.assertTrue(content.is_video(1))

    def test_a_skipped_asset_does_not_shift_the_types(self):
        """media_types is positional, so an asset dropped from media_urls has to
        be dropped from media_types too or every later item reads the wrong
        type."""
        content = self._dispatch(
            [
                _attachment("image", "", has_file=False),
                _attachment("video", "https://cdn.example/b.mp4?sig=x"),
            ]
        )

        self.assertEqual(len(content.media_types), len(content.media_urls))
        self.assertEqual(content.media_types, ["video"])
        self.assertTrue(content.is_video(0))
