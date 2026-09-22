"""Tests for settling posts left in ``publishing``.

Two failures motivate this module, both seen in production:

* a worker killed mid-publish (Heroku's R15 out-of-memory kill) left the row in
  ``publishing`` forever — a status nothing in the engine re-queries and the UI
  renders read-only, so the post could neither finish nor be retried; and
* TikTok's publish API only *accepts* the upload, so a post TikTok later refused
  to process still read "Published".
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.publisher.engine import PublishEngine
from apps.social_accounts.error_messages import (
    PUBLISH_CONFIRM_TIMEOUT_MESSAGE,
    PUBLISH_INTERRUPTED_MESSAGE,
    PUBLISH_UNCONFIRMED_MESSAGE,
)
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers.types import PublishState, PublishStatus


def _status(state, **kwargs):
    return PublishStatus(state=state, **kwargs)


class PendingPublishTestCase(TestCase):
    """Fixture: one TikTok platform post parked in ``publishing``."""

    platform = "tiktok"

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            account_platform_id="tt-1",
            account_name="acct",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, caption="hi")
        self.pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHING,
        )

    def _age(self, **delta):
        """Backdate ``updated_at``, which auto_now would otherwise overwrite."""
        PlatformPost.objects.filter(pk=self.pp.pk).update(updated_at=timezone.now() - timedelta(**delta))
        self.pp.refresh_from_db()

    def _sweep(self, provider=None):
        provider = provider or MagicMock(publish_is_async=True)
        with patch(
            "apps.publisher.engine._provider_and_access_token",
            return_value=(provider, "token"),
        ):
            settled = PublishEngine().confirm_pending_publishes()
        self.pp.refresh_from_db()
        return settled


class StrandedPublishTest(PendingPublishTestCase):
    """The reaper: rows whose worker died before recording anything."""

    def test_stale_row_without_a_handle_is_failed(self):
        self._age(hours=1)

        settled = self._sweep()

        assert settled == 1
        assert self.pp.status == PlatformPost.Status.FAILED
        assert self.pp.publish_error == PUBLISH_INTERRUPTED_MESSAGE

    def test_fresh_row_without_a_handle_is_left_alone(self):
        """A publish in progress is indistinguishable from a dead one except by age."""
        settled = self._sweep()

        assert settled == 0
        assert self.pp.status == PlatformPost.Status.PUBLISHING

    def test_failed_row_becomes_editable_and_selectable_again(self):
        """The point of failing it: ``publishing`` is a dead end for the user."""
        self._age(hours=1)
        self._sweep()

        assert self.pp.status not in PlatformPost.PROTECTED_STATUSES
        assert self.pp.is_bulk_selectable is True

    @override_settings(PUBLISHER_STALE_PUBLISHING_TIMEOUT=10)
    def test_timeout_is_configurable(self):
        """The timeout is read per call, so the setting genuinely takes effect.

        Read at import time instead, this decorator would be a no-op and the
        test would prove nothing.
        """
        self._age(seconds=30)

        self._sweep()

        assert self.pp.status == PlatformPost.Status.FAILED

    @override_settings(PUBLISHER_STALE_PUBLISHING_TIMEOUT=3600)
    def test_a_raised_timeout_keeps_the_row_in_flight(self):
        self._age(seconds=1800)

        self._sweep()

        assert self.pp.status == PlatformPost.Status.PUBLISHING

    def test_a_provider_failure_does_not_abort_the_whole_sweep(self):
        """One unbuildable provider must not strand every other in-flight row."""
        self._age(hours=1)
        other = Post.objects.create(workspace=self.workspace, caption="second")
        second = PlatformPost.objects.create(
            post=other,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHING,
            platform_post_id="v_pub_file~boom",
        )
        PlatformPost.objects.filter(pk=second.pk).update(updated_at=timezone.now() - timedelta(hours=1))

        with patch(
            "apps.publisher.engine._provider_and_access_token",
            side_effect=RuntimeError("no credentials"),
        ):
            PublishEngine().confirm_pending_publishes()

        self.pp.refresh_from_db()
        assert self.pp.status == PlatformPost.Status.FAILED


class AsyncPublishConfirmationTest(PendingPublishTestCase):
    """TikTok-style providers: the upload landed, the publish may not have."""

    def setUp(self):
        super().setUp()
        PlatformPost.objects.filter(pk=self.pp.pk).update(platform_post_id="v_pub_file~abc")
        self.pp.refresh_from_db()

    def test_complete_publishes_with_the_real_video_id(self):
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.return_value = _status(
            PublishState.COMPLETE, platform_post_id="7412345678901234567"
        )

        settled = self._sweep(provider)

        assert settled == 1
        assert self.pp.status == PlatformPost.Status.PUBLISHED
        assert self.pp.platform_post_id == "7412345678901234567"
        assert self.pp.published_at is not None
        provider.check_publish_status.assert_called_once_with("token", "v_pub_file~abc")

    def test_platform_failure_is_surfaced_verbatim(self):
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.return_value = _status(
            PublishState.FAILED, error="TikTok could not process the video (duration_check_failed)."
        )

        self._sweep(provider)

        assert self.pp.status == PlatformPost.Status.FAILED
        assert "duration_check_failed" in self.pp.publish_error

    def test_still_processing_is_left_in_flight(self):
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.return_value = _status(PublishState.PENDING)

        settled = self._sweep(provider)

        assert settled == 0
        assert self.pp.status == PlatformPost.Status.PUBLISHING

    def test_processing_past_the_confirm_timeout_is_failed(self):
        self._age(hours=2)
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.return_value = _status(PublishState.PENDING)

        self._sweep(provider)

        assert self.pp.status == PlatformPost.Status.FAILED
        assert self.pp.publish_error == PUBLISH_CONFIRM_TIMEOUT_MESSAGE

    def test_an_unreachable_platform_does_not_fail_the_post(self):
        """Our inability to ask is not the post's failure."""
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.side_effect = RuntimeError("connection reset")

        settled = self._sweep(provider)

        assert settled == 0
        assert self.pp.status == PlatformPost.Status.PUBLISHING

    def test_an_outage_keeps_reconciling_past_the_processing_timeout(self):
        """ "Cannot ask" must not decay into "the platform said no".

        The upload was accepted, so the post may be live. Failing it on the
        30-minute processing budget would tell the user to publish again — and
        a duplicate video on a live account cannot be taken back.
        """
        self._age(hours=2)  # well past PUBLISH_CONFIRM_TIMEOUT
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.side_effect = RuntimeError("connection reset")

        settled = self._sweep(provider)

        assert settled == 0
        assert self.pp.status == PlatformPost.Status.PUBLISHING

    def test_an_outage_recovers_and_confirms_against_the_original_handle(self):
        """The whole point of holding on: the real answer can still arrive."""
        self._age(hours=2)
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.side_effect = RuntimeError("connection reset")
        self._sweep(provider)

        provider.check_publish_status.side_effect = None
        provider.check_publish_status.return_value = _status(
            PublishState.COMPLETE, platform_post_id="7412345678901234567"
        )
        self._sweep(provider)

        assert self.pp.status == PlatformPost.Status.PUBLISHED
        assert self.pp.platform_post_id == "7412345678901234567"
        # Reconciled against the handle recorded at upload time.
        assert provider.check_publish_status.call_args.args[1] == "v_pub_file~abc"

    def test_a_prolonged_outage_ends_as_unknown_not_as_rejected(self):
        self._age(hours=12)  # past PUBLISHER_UNCONFIRMED_TIMEOUT
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.side_effect = RuntimeError("connection reset")

        self._sweep(provider)

        assert self.pp.status == PlatformPost.Status.FAILED
        assert self.pp.publish_error == PUBLISH_UNCONFIRMED_MESSAGE
        # Never the "try publishing it again" copy — that invites a duplicate.
        assert "try publishing it again" not in self.pp.publish_error.lower()
        assert "check the account" in self.pp.publish_error.lower()

    def test_the_handle_survives_so_the_post_can_still_be_reconciled(self):
        """Only an explicit re-schedule may drop it; giving up must not."""
        self._age(hours=12)
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.side_effect = RuntimeError("connection reset")

        self._sweep(provider)

        assert self.pp.platform_post_id == "v_pub_file~abc"

    def test_a_handle_on_a_sync_provider_is_not_proof_of_success(self):
        """A handle can belong to an *earlier* publish of the same row.

        ``platform_post_id`` used to survive a transition back to ``scheduled``,
        so treating "has a handle" as "went out" would report a publish that
        never left the worker as live. There is no status endpoint to ask, so
        the only honest outcome is the interrupted failure.
        """
        self._age(hours=1)
        provider = MagicMock(publish_is_async=False)

        self._sweep(provider)

        assert self.pp.status == PlatformPost.Status.FAILED
        assert self.pp.publish_error == PUBLISH_INTERRUPTED_MESSAGE

    def test_a_fresh_sync_row_is_left_alone(self):
        provider = MagicMock(publish_is_async=False)

        settled = self._sweep(provider)

        assert settled == 0
        assert self.pp.status == PlatformPost.Status.PUBLISHING

    def test_an_unimplemented_status_check_is_not_treated_as_success(self):
        """Declaring publish_is_async without a checker tells us nothing."""
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.side_effect = NotImplementedError

        settled = self._sweep(provider)

        assert settled == 0
        assert self.pp.status == PlatformPost.Status.PUBLISHING

    def test_an_unimplemented_status_check_ends_as_unknown(self):
        self._age(hours=12)
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.side_effect = NotImplementedError

        self._sweep(provider)

        assert self.pp.status == PlatformPost.Status.FAILED
        assert self.pp.publish_error == PUBLISH_UNCONFIRMED_MESSAGE

    def test_confirmation_never_republishes(self):
        """A duplicate video on a live account cannot be taken back."""
        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.return_value = _status(PublishState.PENDING)

        self._sweep(provider)

        provider.publish_post.assert_not_called()


class ConfirmedPublishLeavesQueueTest(PendingPublishTestCase):
    """A confirmed publish must free its queue slot, like the sync path does."""

    def test_queue_entry_is_dropped(self):
        from apps.calendar.models import Queue, QueueEntry

        queue = Queue.objects.create(workspace=self.workspace, social_account=self.account, name="Q")
        QueueEntry.objects.create(queue=queue, post=self.post, position=0)
        PlatformPost.objects.filter(pk=self.pp.pk).update(platform_post_id="v_pub_file~abc")

        provider = MagicMock(publish_is_async=True)
        provider.check_publish_status.return_value = _status(PublishState.COMPLETE, platform_post_id="7412345678901")
        self._sweep(provider)

        assert not QueueEntry.objects.filter(post=self.post).exists()


class PublishFailureNotifiesAuthorTest(PendingPublishTestCase):
    """A failed post that nobody is told about is how a broken platform goes a day unnoticed."""

    def test_author_is_notified(self):
        from apps.accounts.models import User

        author = User.objects.create_user(
            email="author@example.com",
            password="pw",
            name="Author",
            tos_accepted_at=timezone.now(),
        )
        Post.objects.filter(pk=self.post.pk).update(author=author)
        self._age(hours=1)

        with patch("apps.notifications.engine.notify") as notify:
            self._sweep()

        assert notify.call_count == 1
        assert notify.call_args.args[0] == author

    def test_an_authorless_post_still_fails_cleanly(self):
        self._age(hours=1)

        self._sweep()

        assert self.pp.status == PlatformPost.Status.FAILED

    def test_a_broken_notification_cannot_unwind_the_failure(self):
        self._age(hours=1)

        with patch("apps.notifications.engine.notify", side_effect=RuntimeError("smtp down")):
            self._sweep()

        assert self.pp.status == PlatformPost.Status.FAILED
