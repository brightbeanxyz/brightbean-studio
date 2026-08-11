"""Async publish verification.

TikTok accepts an upload and then validates the file asynchronously — a post
can be "published" in our DB while TikTok has already rejected it
(picture_size_check_failed, frame_rate_check_failed; both hit in production).
The engine must verify async platforms after publishing and surface failures.
"""

from unittest.mock import MagicMock, patch

from background_task.models import Task
from django.test import TestCase
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.publisher.models import PublishLog
from apps.publisher.tasks import VERIFY_MAX_ATTEMPTS, verify_platform_post_publish
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers.types import PostType, PublishResult


def _verifying_provider(verdict):
    provider = MagicMock()
    provider.verifies_publish_async = True
    provider.verify_publish = MagicMock(return_value=verdict)
    return provider


class VerifyTaskTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-user-1",
            account_name="Test TikTok",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi")
        self.platform_post = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="v_pub_file~v2-1.123",
            published_at=timezone.now(),
        )

    def _run(self, provider, attempt=1):
        with patch(
            "apps.publisher.engine._provider_and_access_token",
            return_value=(provider, "token"),
        ):
            verify_platform_post_publish.task_function(str(self.platform_post.id), attempt)

    def test_a_failed_async_check_flips_the_post_to_failed(self):
        self._run(_verifying_provider({"state": "failed", "reason": "frame_rate_check_failed"}))

        self.platform_post.refresh_from_db()
        assert self.platform_post.status == PlatformPost.Status.FAILED
        # publish_error is user-facing: friendly hint, not just the raw code
        assert "frame rate" in self.platform_post.publish_error.lower()
        log = PublishLog.objects.filter(platform_post=self.platform_post).latest("created_at")
        assert "frame_rate_check_failed" in (log.error_message or "")

    def test_a_complete_check_leaves_the_post_published(self):
        self._run(_verifying_provider({"state": "complete"}))

        self.platform_post.refresh_from_db()
        assert self.platform_post.status == PlatformPost.Status.PUBLISHED
        assert not Task.objects.filter(task_name__contains="verify_platform_post_publish").exists()

    def test_processing_reschedules_until_the_attempt_budget(self):
        self._run(_verifying_provider({"state": "processing"}), attempt=1)

        self.platform_post.refresh_from_db()
        assert self.platform_post.status == PlatformPost.Status.PUBLISHED
        assert Task.objects.filter(task_name__contains="verify_platform_post_publish").exists()

    def test_processing_at_the_final_attempt_gives_up_and_stays_published(self):
        self._run(_verifying_provider({"state": "processing"}), attempt=VERIFY_MAX_ATTEMPTS)

        self.platform_post.refresh_from_db()
        assert self.platform_post.status == PlatformPost.Status.PUBLISHED
        assert not Task.objects.filter(task_name__contains="verify_platform_post_publish").exists()

    def test_a_post_no_longer_published_is_left_alone(self):
        self.platform_post.status = PlatformPost.Status.FAILED
        self.platform_post.save()
        provider = _verifying_provider({"state": "complete"})

        self._run(provider)

        provider.verify_publish.assert_not_called()


class EngineSchedulesVerificationTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-user-1",
            account_name="Test TikTok",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi")
        self.platform_post = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.SCHEDULED,
        )

    def _publish(self, provider):
        from apps.publisher.engine import PublishEngine

        with patch(
            "apps.publisher.engine._provider_and_access_token",
            return_value=(provider, "token"),
        ):
            PublishEngine()._publish_platform_post(self.platform_post)

    def test_engine_schedules_verification_for_async_providers(self):
        provider = MagicMock()
        provider.verifies_publish_async = True
        provider.supported_post_types = [PostType.VIDEO, PostType.SHORT]
        provider.publish_post = MagicMock(
            return_value=PublishResult(platform_post_id="v_pub~1", url="", extra={})
        )

        self._publish(provider)

        self.platform_post.refresh_from_db()
        assert self.platform_post.status == PlatformPost.Status.PUBLISHED
        assert Task.objects.filter(task_name__contains="verify_platform_post_publish").exists()

    def test_engine_does_not_schedule_verification_for_sync_providers(self):
        provider = MagicMock()
        provider.verifies_publish_async = False
        provider.supported_post_types = [PostType.VIDEO, PostType.SHORT]
        provider.publish_post = MagicMock(
            return_value=PublishResult(platform_post_id="fb-1", url="", extra={})
        )

        self._publish(provider)

        self.platform_post.refresh_from_db()
        assert self.platform_post.status == PlatformPost.Status.PUBLISHED
        assert not Task.objects.filter(task_name__contains="verify_platform_post_publish").exists()
