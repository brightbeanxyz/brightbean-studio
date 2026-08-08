"""Tests for first-comment posting.

The failure these cover is a silent one: a Facebook post published with a first
comment where the comment never appeared, while the post showed as fully
published and nothing in the database recorded that anything had gone wrong.
"""

from unittest.mock import MagicMock, patch

from django.db import OperationalError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.publisher.engine import (
    FIRST_COMMENT_MAX_RETRIES,
    FIRST_COMMENT_RETRY_BACKOFF,
    PublishEngine,
    _can_reconcile_comments,
    _first_comment_delay,
    _is_ambiguous_submission_failure,
    _post_first_comment_task,
)
from apps.social_accounts.error_messages import (
    FIRST_COMMENT_RECONNECT_MESSAGE,
    FIRST_COMMENT_REJECTED_MESSAGE,
    FIRST_COMMENT_TEMPORARY_MESSAGE,
)
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers.exceptions import APIError, PublishError, RateLimitError
from providers.types import CommentResult

Status = PlatformPost.FirstCommentStatus


class FirstCommentTaskTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="page-1",
            account_name="Test Page",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(
            workspace=self.workspace,
            caption="hi",
            first_comment="More detail in the comments",
        )
        self.platform_post = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="post-1",
            published_at=timezone.now(),
        )

    def _run(self, provider):
        """Run the task body directly, bypassing the background-task queue."""
        with patch(
            "apps.publisher.engine._provider_and_access_token",
            return_value=(provider, "page-token"),
        ):
            _post_first_comment_task.task_function(str(self.platform_post.id))

    # -- success -------------------------------------------------------

    def test_success_records_the_comment_id(self):
        provider = MagicMock()
        provider.publish_comment.return_value = CommentResult(platform_comment_id="comment-1")

        self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.POSTED)
        self.assertEqual(self.platform_post.first_comment_id, "comment-1")
        self.assertEqual(self.platform_post.first_comment_error, "")
        self.assertIsNotNone(self.platform_post.first_comment_posted_at)
        provider.publish_comment.assert_called_once_with(
            access_token="page-token",
            post_id="post-1",
            text="More detail in the comments",
        )

    def test_an_already_posted_comment_is_never_posted_twice(self):
        """Two publish paths and a retry queue can each reach this task for the
        same row. Commenting twice on a live post is not recoverable."""
        self.platform_post.first_comment_status = Status.POSTED
        self.platform_post.save(update_fields=["first_comment_status"])
        provider = MagicMock()

        self._run(provider)

        provider.publish_comment.assert_not_called()

    def test_a_missing_platform_post_id_fails_permanently(self):
        self.platform_post.platform_post_id = ""
        self.platform_post.save(update_fields=["platform_post_id"])
        provider = MagicMock()

        self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.FAILED)
        provider.publish_comment.assert_not_called()

    # -- failure -------------------------------------------------------

    def test_a_retryable_failure_is_recorded_and_requeued(self):
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError("transient", status_code=500, platform="Facebook")

        # A 5xx is ambiguous, so it only stays retryable for a provider that can
        # check first whether the comment landed — which Facebook can.
        with (
            patch("apps.publisher.engine._can_reconcile_comments", return_value=True),
            patch("apps.publisher.engine._post_first_comment_task") as requeue,
        ):
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)
        self.assertEqual(self.platform_post.first_comment_retry_count, 1)
        # The stored text is what the composer renders, so it carries none of
        # the platform's response body.
        self.assertEqual(self.platform_post.first_comment_error, FIRST_COMMENT_TEMPORARY_MESSAGE)
        requeue.assert_called_once_with(str(self.platform_post.id), schedule=FIRST_COMMENT_RETRY_BACKOFF[0])

    def test_a_non_retryable_failure_is_not_requeued(self):
        """A missing pages_manage_engagement grant will fail identically three
        times — record it and stop."""
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError(
            "(#200) Requires pages_manage_engagement",
            status_code=403,
            platform="Facebook",
            retryable=False,
        )

        with patch("apps.publisher.engine._post_first_comment_task") as requeue:
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.FAILED)
        self.assertEqual(self.platform_post.first_comment_error, FIRST_COMMENT_RECONNECT_MESSAGE)
        self.assertNotIn("pages_manage_engagement", self.platform_post.first_comment_error)
        requeue.assert_not_called()

    def test_a_clean_4xx_is_not_retried(self):
        """The regression test for four identical comments on one post.

        Instagram answered a comment POST carrying an unsupported ``fields``
        param with a 400 *after* creating the comment. Re-sending the identical
        request earned the identical answer three more times.
        """
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError(
            'Instagram API error 400: {"error":{"message":"This API call does not support the requested '
            'response format","type":"OAuthException","code":20,"error_subcode":1772107}}',
            status_code=400,
            platform="Instagram",
        )

        with patch("apps.publisher.engine._post_first_comment_task") as requeue:
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.FAILED)
        requeue.assert_not_called()

    def test_an_auth_rejection_is_retried_so_the_refreshed_token_can_be_used(self):
        """_provider_and_access_token refreshes an expiring token between
        attempts, so a 401 retry really is a different request."""
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError("expired", status_code=401, platform="Instagram")

        with patch("apps.publisher.engine._post_first_comment_task") as requeue:
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)
        requeue.assert_called_once()

    def test_a_permission_rejection_is_not_retried(self):
        """403 means a missing scope or a revoked grant: a reconnect, not a
        backoff."""
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError("no scope", status_code=403, platform="Instagram")

        with patch("apps.publisher.engine._post_first_comment_task") as requeue:
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.FAILED)
        requeue.assert_not_called()

    def test_the_stored_error_never_contains_the_platform_response(self):
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError(
            'Instagram API error 400: {"error":{"message":"This API call does not support the requested '
            'response format","type":"OAuthException","code":20,"error_subcode":1772107,'
            '"error_user_msg":"Your Instagram comment was not added","fbtrace_id":"A4B_mFUQTXKx"}}',
            status_code=400,
            platform="Instagram",
        )

        self._run(provider)

        self.platform_post.refresh_from_db()
        stored = self.platform_post.first_comment_error
        self.assertEqual(stored, FIRST_COMMENT_REJECTED_MESSAGE)
        self.assertNotIn("OAuthException", stored)
        self.assertNotIn("fbtrace_id", stored)

    def test_the_raw_platform_error_still_reaches_the_logs(self):
        """Storing friendly text must not cost operators the diagnostic."""
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError(
            'Instagram API error 400: {"error":{"code":20,"fbtrace_id":"A4B_mFUQTXKx"}}',
            status_code=400,
            platform="Instagram",
        )

        with self.assertLogs("apps.publisher.engine", level="WARNING") as logs:
            self._run(provider)

        self.assertIn("fbtrace_id", "\n".join(logs.output))

    def test_a_message_we_wrote_ourselves_is_shown_as_is(self):
        """PublishError text is authored for a human and is worth keeping."""
        provider = MagicMock()
        provider.publish_comment.side_effect = PublishError(
            "Instagram container processing timed out",
            platform="Instagram",
            retryable=False,
        )

        self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_error, "Instagram container processing timed out")

    def test_a_rate_limit_uses_the_platforms_retry_after(self):
        provider = MagicMock()
        provider.publish_comment.side_effect = RateLimitError("slow down", retry_after=900, platform="Facebook")

        with patch("apps.publisher.engine._post_first_comment_task") as requeue:
            self._run(provider)

        requeue.assert_called_once_with(str(self.platform_post.id), schedule=900)

    def test_retries_stop_after_the_maximum(self):
        self.platform_post.first_comment_retry_count = FIRST_COMMENT_MAX_RETRIES
        self.platform_post.save(update_fields=["first_comment_retry_count"])
        provider = MagicMock()
        provider.find_own_comment.return_value = None
        provider.publish_comment.side_effect = APIError("still failing", status_code=500, platform="Facebook")

        with (
            patch("apps.publisher.engine._can_reconcile_comments", return_value=True),
            patch("apps.publisher.engine._post_first_comment_task") as requeue,
        ):
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.FAILED)
        requeue.assert_not_called()

    def test_an_unsupported_platform_is_not_recorded_as_a_failure(self):
        provider = MagicMock()
        provider.publish_comment.side_effect = NotImplementedError()

        self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.NONE)

    # -- token refresh -------------------------------------------------

    def test_an_expiring_token_is_refreshed_before_commenting(self):
        """The comment fires minutes after the publish — long enough for a token
        that was fine at publish time to have gone stale."""
        self.account.token_expires_at = timezone.now()
        self.account.oauth_refresh_token = "refresh-me"
        self.account.save(update_fields=["token_expires_at", "oauth_refresh_token"])

        provider = MagicMock()
        provider.publish_comment.return_value = CommentResult(platform_comment_id="comment-1")

        with (
            patch("apps.publisher.engine.get_provider", return_value=provider),
            patch("apps.publisher.engine._resolve_publish_credentials", return_value={}),
            patch.object(SocialAccount, "refresh_oauth_token", return_value="fresh-token") as refresh,
        ):
            _post_first_comment_task.task_function(str(self.platform_post.id))

        refresh.assert_called_once()
        self.assertEqual(provider.publish_comment.call_args.kwargs["access_token"], "fresh-token")


class ScheduleFirstCommentTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="page-1",
            account_name="Test Page",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi", first_comment="Read more")
        self.platform_post = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="post-1",
        )

    def test_scheduling_marks_the_row_pending(self):
        with patch("apps.publisher.engine._post_first_comment_task") as task:
            PublishEngine()._maybe_schedule_first_comment(self.platform_post)

        task.assert_called_once()
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)

    def test_a_pending_row_is_not_scheduled_again(self):
        self.platform_post.first_comment_status = Status.PENDING
        self.platform_post.save(update_fields=["first_comment_status"])

        with patch("apps.publisher.engine._post_first_comment_task") as task:
            PublishEngine()._maybe_schedule_first_comment(self.platform_post)

        task.assert_not_called()

    def test_a_post_without_a_first_comment_is_not_scheduled(self):
        self.post.first_comment = ""
        self.post.save(update_fields=["first_comment"])
        self.platform_post.refresh_from_db()

        with patch("apps.publisher.engine._post_first_comment_task") as task:
            PublishEngine()._maybe_schedule_first_comment(self.platform_post)

        task.assert_not_called()

    def test_an_unpublished_row_is_not_scheduled(self):
        self.platform_post.status = PlatformPost.Status.FAILED
        self.platform_post.save(update_fields=["status"])

        with patch("apps.publisher.engine._post_first_comment_task") as task:
            PublishEngine()._maybe_schedule_first_comment(self.platform_post)

        task.assert_not_called()

    def test_publishing_on_the_retry_path_still_schedules_the_comment(self):
        """A post that only succeeds on retry used to get no first comment at all."""
        self.platform_post.status = PlatformPost.Status.SCHEDULED
        self.platform_post.retry_count = 1
        self.platform_post.next_retry_at = timezone.now()
        self.platform_post.save(update_fields=["status", "retry_count", "next_retry_at"])

        def fake_publish(pp):
            pp.status = PlatformPost.Status.PUBLISHED
            pp.published_at = timezone.now()
            pp.save(update_fields=["status", "published_at"])
            return {"success": True}

        with (
            patch.object(PublishEngine, "_publish_platform_post", side_effect=fake_publish),
            patch("apps.publisher.engine._post_first_comment_task") as task,
        ):
            PublishEngine()._process_retries()

        task.assert_called_once()
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)


class FirstCommentDurabilityTest(TestCase):
    """A comment that reached the platform must never be posted twice."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="page-1",
            account_name="Test Page",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi", first_comment="Read more")
        self.platform_post = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="post-1",
        )

    def test_a_db_error_after_a_successful_post_does_not_escape_the_task(self):
        """An escaping exception would let django-background-tasks re-run this
        task (default 25 attempts) against a row still marked pending — and
        comment on the live post again."""
        provider = MagicMock()
        provider.publish_comment.return_value = CommentResult(platform_comment_id="comment-1")

        with (
            patch(
                "apps.publisher.engine._provider_and_access_token",
                return_value=(provider, "page-token"),
            ),
            patch.object(PlatformPost.objects, "filter", side_effect=OperationalError("connection reset")),
        ):
            # Must not raise.
            _post_first_comment_task.task_function(str(self.platform_post.id))

        provider.publish_comment.assert_called_once()

    def test_the_retry_counter_increments_atomically(self):
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError("transient", status_code=500, platform="Facebook")

        with (
            patch("apps.publisher.engine._can_reconcile_comments", return_value=True),
            patch(
                "apps.publisher.engine._provider_and_access_token",
                return_value=(provider, "page-token"),
            ),
        ):
            _post_first_comment_task.task_function(str(self.platform_post.id))

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_retry_count, 1)
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)


class FirstCommentDelayTest(TestCase):
    """The delay resolves through the settings cascade, not an import-time constant."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")

    def test_the_app_default_is_used_when_nothing_overrides_it(self):
        self.assertEqual(_first_comment_delay(self.workspace.id), 120)

    def test_a_workspace_override_takes_effect(self):
        from apps.settings_manager.models import WorkspaceSetting

        WorkspaceSetting.objects.create(
            workspace=self.workspace,
            key="publishing.first_comment_delay_seconds",
            value=30,
        )

        self.assertEqual(_first_comment_delay(self.workspace.id), 30)

    def test_an_unresolvable_workspace_falls_back_rather_than_raising(self):
        self.assertEqual(_first_comment_delay("00000000-0000-0000-0000-000000000000"), 120)


class AmbiguousFailureTest(TestCase):
    """A failure that may have created the comment must never be blind-retried."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="page-1",
            account_name="Test Page",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi", first_comment="Read more")
        self.platform_post = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="post-1",
        )

    def _run(self, provider):
        with patch(
            "apps.publisher.engine._provider_and_access_token",
            return_value=(provider, "page-token"),
        ):
            _post_first_comment_task.task_function(str(self.platform_post.id))

    def test_a_reconcilable_provider_may_still_retry_a_5xx(self):
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError("bad gateway", status_code=502, platform="Facebook")

        with (
            patch("apps.publisher.engine._can_reconcile_comments", return_value=True),
            patch("apps.publisher.engine._post_first_comment_task") as requeue,
        ):
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)
        requeue.assert_called_once()

    def test_a_provider_that_cannot_reconcile_stops_after_an_ambiguous_failure(self):
        """Retrying could double-comment and there is no way to check first."""
        provider = MagicMock()
        provider.publish_comment.side_effect = APIError("bad gateway", status_code=502, platform="Facebook")

        with (
            patch("apps.publisher.engine._can_reconcile_comments", return_value=False),
            patch("apps.publisher.engine._post_first_comment_task") as requeue,
        ):
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.FAILED)
        requeue.assert_not_called()

    def test_a_transport_error_with_no_status_code_is_ambiguous(self):
        provider = MagicMock()
        provider.publish_comment.side_effect = TimeoutError("read timed out")

        with (
            patch("apps.publisher.engine._can_reconcile_comments", return_value=False),
            patch("apps.publisher.engine._post_first_comment_task") as requeue,
        ):
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.FAILED)
        requeue.assert_not_called()

    def test_a_rate_limit_is_not_treated_as_ambiguous(self):
        """429 is a rejection before the write, so retrying cannot duplicate."""
        provider = MagicMock()
        provider.publish_comment.side_effect = RateLimitError("slow down", retry_after=60, platform="Facebook")

        with (
            patch("apps.publisher.engine._can_reconcile_comments", return_value=False),
            patch("apps.publisher.engine._post_first_comment_task") as requeue,
        ):
            self._run(provider)

        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)
        requeue.assert_called_once()

    def test_ambiguity_classification(self):
        self.assertTrue(_is_ambiguous_submission_failure(APIError("boom", status_code=500)))
        self.assertTrue(_is_ambiguous_submission_failure(TimeoutError("no status code")))
        self.assertFalse(_is_ambiguous_submission_failure(APIError("nope", status_code=403)))
        self.assertFalse(_is_ambiguous_submission_failure(RateLimitError("429", retry_after=1)))

    def test_only_providers_implementing_the_lookup_can_reconcile(self):
        from providers.facebook import FacebookProvider
        from providers.instagram import InstagramProvider
        from providers.instagram_login import InstagramLoginProvider
        from providers.tiktok import TikTokProvider

        self.assertTrue(_can_reconcile_comments(FacebookProvider({})))
        self.assertTrue(_can_reconcile_comments(InstagramProvider({})))
        self.assertTrue(_can_reconcile_comments(InstagramLoginProvider({})))
        self.assertFalse(_can_reconcile_comments(TikTokProvider({})))

    def test_a_retry_reconciles_before_posting_again(self):
        """The previous attempt may have created the comment before failing."""
        self.platform_post.first_comment_retry_count = 1
        self.platform_post.save(update_fields=["first_comment_retry_count"])

        provider = MagicMock()
        provider.find_own_comment.return_value = "comment-already-there"

        self._run(provider)

        provider.publish_comment.assert_not_called()
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.POSTED)
        self.assertEqual(self.platform_post.first_comment_id, "comment-already-there")

    def test_a_retry_posts_when_no_existing_comment_is_found(self):
        self.platform_post.first_comment_retry_count = 1
        self.platform_post.save(update_fields=["first_comment_retry_count"])

        provider = MagicMock()
        provider.find_own_comment.return_value = None
        provider.publish_comment.return_value = CommentResult(platform_comment_id="comment-2")

        self._run(provider)

        provider.publish_comment.assert_called_once()
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_id, "comment-2")

    def test_a_failed_reconciliation_skips_the_attempt_rather_than_risking_a_duplicate(self):
        self.platform_post.first_comment_retry_count = 1
        self.platform_post.save(update_fields=["first_comment_retry_count"])

        provider = MagicMock()
        provider.find_own_comment.side_effect = APIError("cannot read", status_code=500, platform="Facebook")

        with patch("apps.publisher.engine._post_first_comment_task") as requeue:
            self._run(provider)

        provider.publish_comment.assert_not_called()
        # The attempt still has to be recorded and re-queued. A bare return
        # would leave the row PENDING with no task behind it, and the post would
        # read as fully successful forever.
        self.platform_post.refresh_from_db()
        self.assertEqual(self.platform_post.first_comment_status, Status.PENDING)
        self.assertEqual(self.platform_post.first_comment_retry_count, 2)
        requeue.assert_called_once()

    def test_the_first_attempt_does_not_pay_for_reconciliation(self):
        provider = MagicMock()
        provider.publish_comment.return_value = CommentResult(platform_comment_id="comment-1")

        self._run(provider)

        provider.find_own_comment.assert_not_called()


class FirstCommentDelayCascadeTest(TestCase):
    """PUBLISHER_FIRST_COMMENT_DELAY must actually participate in the cascade."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")

    @override_settings(PUBLISHER_FIRST_COMMENT_DELAY=45)
    def test_the_env_backed_setting_wins_over_the_app_default(self):
        """Without this, get_setting's APP_DEFAULTS floor (120) answers for every
        workspace with no override row and the env var is never consulted."""
        self.assertEqual(_first_comment_delay(self.workspace.id), 45)

    @override_settings(PUBLISHER_FIRST_COMMENT_DELAY=45)
    def test_a_workspace_override_still_outranks_the_setting(self):
        from apps.settings_manager.models import WorkspaceSetting

        WorkspaceSetting.objects.create(
            workspace=self.workspace,
            key="publishing.first_comment_delay_seconds",
            value=30,
        )

        self.assertEqual(_first_comment_delay(self.workspace.id), 30)

    @override_settings(PUBLISHER_FIRST_COMMENT_DELAY=45)
    def test_an_org_override_outranks_the_setting(self):
        from apps.settings_manager.models import OrgSetting

        OrgSetting.objects.create(
            organization=self.org,
            key="publishing.first_comment_delay_seconds",
            value=90,
        )

        self.assertEqual(_first_comment_delay(self.workspace.id), 90)
