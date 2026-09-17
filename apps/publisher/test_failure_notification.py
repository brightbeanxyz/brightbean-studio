"""How many emails a failed publish actually produces.

``_fail_permanently`` acts on a ``PlatformPost``, so a post going to five
channels that fails on all five used to be five separate emails inside the same
second — and a revoked token across two hundred scheduled posts was two hundred.
The existing coverage in ``test_publish_confirmation.py`` asserts
``notify.call_count == 1`` against a single-target fixture, which is exactly why
the fan-out went unnoticed.
"""

from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post
from apps.notifications.engine import send_batched_email_digests
from apps.notifications.models import EventType, Notification
from apps.organizations.models import Organization
from apps.publisher.engine import PublishEngine
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

PLATFORMS = ["tiktok", "youtube", "instagram", "pinterest", "bluesky"]


class PublishFailureFanOutTest(TestCase):
    """One post, five channels, every one of them failing."""

    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com", password="x", name="Author", tos_accepted_at=timezone.now()
        )
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.post = Post.objects.create(workspace=self.workspace, caption="hi", author=self.author)
        self.targets = [
            PlatformPost.objects.create(
                post=self.post,
                social_account=SocialAccount.objects.create(
                    workspace=self.workspace,
                    platform=platform,
                    account_platform_id=f"{platform}-1",
                    account_name="acct",
                    connection_status=SocialAccount.ConnectionStatus.CONNECTED,
                ),
                status=PlatformPost.Status.PUBLISHING,
            )
            for platform in PLATFORMS
        ]
        self.engine = PublishEngine()

    def _fail_all(self):
        for pp in self.targets:
            self.engine._fail_permanently(pp, "boom", user_message="It did not go out.")

    def test_five_failed_targets_send_one_email(self):
        self._fail_all()

        # Every failure is still recorded in-app, one per target — that is where
        # "which channel failed" belongs.
        self.assertEqual(
            Notification.objects.filter(user=self.author, event_type=EventType.POST_FAILED).count(),
            len(PLATFORMS),
        )
        # ...and nothing has been emailed yet.
        self.assertEqual(mail.outbox, [])

        # Past the batching window, it is a single email.
        from apps.notifications.models import NotificationDelivery

        then = timezone.now() - timedelta(minutes=30)
        NotificationDelivery.objects.filter(batch_queued_at__isnull=False).update(batch_queued_at=then, created_at=then)
        self.assertEqual(send_batched_email_digests(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "5 posts failed to publish")

    def test_settling_a_failed_row_again_does_not_notify_again(self):
        """Seven paths reach _fail_permanently. A publish thread still running
        when the confirmation sweep gives up on the same row arrives second."""
        pp = self.targets[0]
        self.engine._fail_permanently(pp, "boom", user_message="It did not go out.")
        self.assertEqual(Notification.objects.filter(user=self.author).count(), 1)

        self.engine._fail_permanently(pp, "boom again", user_message="Still not out.")
        self.assertEqual(Notification.objects.filter(user=self.author).count(), 1)

    def test_a_stale_object_cannot_resurrect_a_settled_row(self):
        """The second caller holds an object loaded *before* the row was
        settled, so its in-memory status still says ``publishing``. Only the
        database can answer who settled it."""
        pp = self.targets[0]
        stale = PlatformPost.objects.get(pk=pp.pk)
        self.assertEqual(stale.status, PlatformPost.Status.PUBLISHING)

        self.engine._fail_permanently(pp, "sweep gave up", user_message="Interrupted.")
        self.assertEqual(Notification.objects.filter(user=self.author).count(), 1)

        self.engine._fail_permanently(stale, "publish thread finished", user_message="Also failed.")

        self.assertEqual(Notification.objects.filter(user=self.author).count(), 1)
        stale.refresh_from_db()
        self.assertEqual(stale.status, PlatformPost.Status.FAILED)

    def test_an_authorless_post_still_fails_cleanly(self):
        self.post.author = None
        self.post.save(update_fields=["author"])
        pp = PlatformPost.objects.get(pk=self.targets[0].pk)

        self.engine._fail_permanently(pp, "boom", user_message="It did not go out.")

        pp.refresh_from_db()
        self.assertEqual(pp.status, PlatformPost.Status.FAILED)
        self.assertEqual(Notification.objects.count(), 0)

    def test_a_published_post_is_never_walked_back_to_failed(self):
        """``published`` has no outgoing edge in VALID_TRANSITIONS, and for good
        reason: the post is live on a real account. A slow publish thread
        finishing after the confirmation sweep confirmed it must not overwrite
        that, tell the author it failed, and offer a retry that double-posts."""
        pp = self.targets[0]
        self.engine._mark_confirmed_published(pp, "platform-live-id")
        pp.refresh_from_db()
        self.assertEqual(pp.status, PlatformPost.Status.PUBLISHED)

        # The publish thread still believes it is mid-flight.
        stale = PlatformPost.objects.get(pk=pp.pk)
        stale.status = PlatformPost.Status.PUBLISHING

        self.engine._fail_permanently(stale, "thread timed out", user_message="It did not go out.")

        pp.refresh_from_db()
        self.assertEqual(pp.status, PlatformPost.Status.PUBLISHED)
        self.assertEqual(pp.platform_post_id, "platform-live-id")
        self.assertEqual(Notification.objects.count(), 0)

    def test_a_lost_race_leaves_the_caller_holding_the_truth(self):
        """When someone else settled the row, the in-memory object has to agree
        with the database — not with the write that was refused."""
        pp = self.targets[0]
        self.engine._mark_confirmed_published(pp, "platform-live-id")

        stale = PlatformPost.objects.get(pk=pp.pk)
        stale.status = PlatformPost.Status.PUBLISHING
        self.engine._fail_permanently(stale, "thread timed out", user_message="It did not go out.")

        self.assertEqual(stale.status, PlatformPost.Status.PUBLISHED)
        self.assertNotEqual(stale.publish_error, "It did not go out.")

    def test_a_row_put_back_for_a_retry_is_not_failed_by_a_slow_thread(self):
        """A thread that fails slowly can finish after _schedule_retry has
        already re-queued the row. Overwriting that would throw away a pending
        retry and email a failure that has not happened yet."""
        pp = self.targets[0]
        stale = PlatformPost.objects.get(pk=pp.pk)

        # Another path re-queues it for another attempt.
        retry_at = timezone.now() + timedelta(minutes=5)
        PlatformPost.objects.filter(pk=pp.pk).update(
            status=PlatformPost.Status.SCHEDULED, retry_count=1, next_retry_at=retry_at
        )

        self.engine._fail_permanently(stale, "slow failure", user_message="It did not go out.")

        pp.refresh_from_db()
        self.assertEqual(pp.status, PlatformPost.Status.SCHEDULED)
        self.assertEqual(pp.retry_count, 1)
        self.assertIsNotNone(pp.next_retry_at)
        self.assertEqual(Notification.objects.count(), 0)

    def test_a_row_that_was_never_claimed_is_reported_loudly(self):
        """If a caller ever reaches here without claiming the row into
        publishing, the post would silently never fail. That has to be visible."""
        pp = self.targets[0]
        PlatformPost.objects.filter(pk=pp.pk).update(status=PlatformPost.Status.DRAFT)
        pp.status = PlatformPost.Status.PUBLISHING

        with self.assertLogs("apps.publisher.engine", level="WARNING") as logs:
            self.engine._fail_permanently(pp, "boom", user_message="It did not go out.")

        self.assertTrue(any("expected 'publishing'" in line for line in logs.output))
        self.assertEqual(Notification.objects.count(), 0)
