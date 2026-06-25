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
