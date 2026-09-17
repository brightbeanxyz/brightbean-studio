"""Publish-failure email is collapsed into one message per user.

The bug this closes: a revoked token fails every scheduled post at once, one
``PlatformPost`` at a time, and each one used to send its own email — 200 of
them inside a minute to a single address, repeatedly, until the day's Resend
quota was gone.
"""

import contextlib
import datetime
from unittest.mock import patch

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.notifications.engine import (
    BATCH_CLAIM_TIMEOUT,
    BATCH_MAX_ITEMS,
    BATCH_SIZE_TRIGGER,
    BATCH_WINDOW_MINUTES,
    MAX_RETRY_ATTEMPTS,
    notify,
    send_batched_email_digests,
)
from apps.notifications.models import (
    Channel,
    DeliveryStatus,
    EventType,
    Notification,
    NotificationDelivery,
    NotificationPreference,
)


def fail(user, n=1, title="TikTok post failed to publish"):
    for i in range(n):
        notify(user, EventType.POST_FAILED, title, body=f"reason {i}")


def age_the_queue(minutes):
    """Push every queued row back in time so its batching window has closed."""
    then = timezone.now() - datetime.timedelta(minutes=minutes)
    NotificationDelivery.objects.filter(batch_queued_at__isnull=False).update(batch_queued_at=then, created_at=then)


@pytest.mark.django_db
def test_a_storm_of_failures_becomes_one_email(user):
    fail(user, 300)

    # Nothing has gone out yet: notify() queues, it does not send.
    assert mail.outbox == []
    # ...but every failure is still recorded in-app, which is where the detail
    # belongs. Nothing is lost by not mailing it.
    assert Notification.objects.filter(user=user, event_type=EventType.POST_FAILED).count() == 300

    assert send_batched_email_digests() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "300 posts failed to publish"
    assert mail.outbox[0].to == [user.email]

    assert NotificationDelivery.objects.filter(channel=Channel.EMAIL, status=DeliveryStatus.DELIVERED).count() == 300


@pytest.mark.django_db
def test_one_failure_says_post_not_posts(user):
    fail(user, 1)
    age_the_queue(BATCH_WINDOW_MINUTES + 1)
    send_batched_email_digests()
    assert mail.outbox[0].subject == "1 post failed to publish"


@pytest.mark.django_db
def test_a_single_failure_waits_for_the_batching_window(user):
    """The whole point of waiting: the failure arriving ten seconds from now
    belongs in the same email as this one."""
    fail(user, 1)

    assert send_batched_email_digests() == 0
    assert mail.outbox == []

    age_the_queue(BATCH_WINDOW_MINUTES + 1)
    assert send_batched_email_digests() == 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_a_storm_does_not_wait(user):
    """Past the size trigger it is a storm, not a trickle — no reason to make
    the user watch it build."""
    fail(user, BATCH_SIZE_TRIGGER)
    assert send_batched_email_digests() == 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_long_lists_are_truncated(user):
    fail(user, BATCH_MAX_ITEMS + 7)
    send_batched_email_digests()
    assert "and 7 more" in mail.outbox[0].body


@pytest.mark.django_db
def test_opting_out_of_the_email_opts_out_of_the_digest(user):
    NotificationPreference.objects.create(
        user=user, event_type=EventType.POST_FAILED, channel=Channel.EMAIL, is_enabled=False
    )
    fail(user, 20)

    assert send_batched_email_digests() == 0
    assert mail.outbox == []
    # The in-app notification is unaffected — they opted out of email, not of
    # being told.
    assert Notification.objects.filter(user=user).count() == 20


@pytest.mark.django_db
def test_an_interrupted_inline_delivery_is_never_swept_into_a_digest(user):
    """A deploy or an OOM kill mid-send leaves a PENDING row with no
    next_retry_at. That is NOT a queued row, and folding it into a digest would
    mark an invitation delivered that was never sent."""
    orphan_notification = Notification.objects.create(
        user=user, event_type=EventType.TEAM_MEMBER_INVITED, title="You've been invited"
    )
    orphan = NotificationDelivery.objects.create(
        notification=orphan_notification,
        channel=Channel.EMAIL,
        status=DeliveryStatus.PENDING,
        next_retry_at=None,
        batch_queued_at=None,
    )

    fail(user, BATCH_SIZE_TRIGGER)
    send_batched_email_digests()

    orphan.refresh_from_db()
    assert orphan.status == DeliveryStatus.PENDING
    assert len(mail.outbox) == 1
    assert "invited" not in mail.outbox[0].body


@pytest.mark.django_db
def test_the_retry_sweep_never_touches_a_queued_row(user):
    """Queued rows keep next_retry_at NULL; retry_failed_deliveries() requires a
    non-null one. The two sweeps can never both own a row."""
    from apps.notifications.engine import retry_failed_deliveries

    fail(user, 5)
    assert retry_failed_deliveries() == 0
    assert mail.outbox == []


@pytest.mark.django_db
def test_a_claimed_batch_is_not_sent_twice(user):
    """Simulates a second sweep arriving while the first still holds the claim."""
    fail(user, BATCH_SIZE_TRIGGER)
    NotificationDelivery.objects.filter(batch_queued_at__isnull=False).update(batch_claimed_at=timezone.now())

    assert send_batched_email_digests() == 0
    assert mail.outbox == []


@pytest.mark.django_db
def test_an_abandoned_claim_is_taken_over(user):
    """A sweep that died holding the claim must not strand the rows for good."""
    fail(user, BATCH_SIZE_TRIGGER)
    abandoned = timezone.now() - BATCH_CLAIM_TIMEOUT - datetime.timedelta(minutes=1)
    NotificationDelivery.objects.filter(batch_queued_at__isnull=False).update(batch_claimed_at=abandoned)

    assert send_batched_email_digests() == 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_a_failed_send_releases_the_claim_and_charges_an_attempt(user):
    fail(user, BATCH_SIZE_TRIGGER)

    with patch("apps.notifications.engine._send_digest_email", side_effect=RuntimeError("smtp down")):
        assert send_batched_email_digests() == 0

    rows = NotificationDelivery.objects.filter(batch_queued_at__isnull=False)
    assert all(r.batch_claimed_at is None for r in rows), "the claim must be released for the next run"
    assert all(r.attempts == 1 for r in rows)
    assert all(r.status == DeliveryStatus.PENDING for r in rows)

    # The next run picks them straight back up.
    assert send_batched_email_digests() == 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_a_batch_gives_up_after_the_retry_budget(user):
    fail(user, BATCH_SIZE_TRIGGER)

    with patch("apps.notifications.engine._send_digest_email", side_effect=RuntimeError("smtp down")):
        for _ in range(MAX_RETRY_ATTEMPTS):
            send_batched_email_digests()

    assert not NotificationDelivery.objects.filter(status=DeliveryStatus.PENDING).exists()
    assert NotificationDelivery.objects.filter(status=DeliveryStatus.FAILED).count() == BATCH_SIZE_TRIGGER
    assert mail.outbox == []


@pytest.mark.django_db
def test_two_users_get_their_own_digest(user, django_user_model):
    other = django_user_model.objects.create_user(
        email="other@example.com", password="x", name="Other", tos_accepted_at=timezone.now()
    )
    fail(user, BATCH_SIZE_TRIGGER)
    fail(other, BATCH_SIZE_TRIGGER)

    assert send_batched_email_digests() == 2
    assert sorted(m.to[0] for m in mail.outbox) == sorted([user.email, other.email])


@pytest.mark.django_db
def test_an_unbatched_event_still_sends_immediately(user):
    """Only the events in BATCHED_EMAIL_EVENTS are held back."""
    notify(user, EventType.SOCIAL_ACCOUNT_DISCONNECTED, "TikTok disconnected")
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_a_digest_the_budget_drops_is_not_recorded_as_delivered(user):
    """A dropped email raises nothing, so treating silence as success would put
    a lie in the delivery table — which is the system of record."""
    fail(user, BATCH_SIZE_TRIGGER)

    with patch("apps.notifications.engine.EmailMultiAlternatives.send", return_value=0):
        assert send_batched_email_digests() == 0

    rows = NotificationDelivery.objects.filter(batch_queued_at__isnull=False)
    assert all(r.status == DeliveryStatus.FAILED for r in rows)
    assert all(r.batch_claimed_at is None for r in rows)
    assert not NotificationDelivery.objects.filter(status=DeliveryStatus.DELIVERED, channel=Channel.EMAIL).exists()


@pytest.mark.django_db
def test_the_backlog_drains_oldest_first(django_user_model, monkeypatch):
    """An unordered LIMIT lets Postgres return whichever groups it likes, and
    return the same ones every run — so a backlog wider than the cap could
    starve some users indefinitely."""
    monkeypatch.setattr("apps.notifications.engine.BATCH_GROUP_LIMIT", 2)

    users = []
    for i in range(4):
        u = django_user_model.objects.create_user(
            email=f"u{i}@example.com", password="x", name=f"U{i}", tos_accepted_at=timezone.now()
        )
        fail(u, 1)
        # Each user's batch is older than the last, so "oldest first" has a
        # definite answer to check against.
        NotificationDelivery.objects.filter(notification__user=u, batch_queued_at__isnull=False).update(
            batch_queued_at=timezone.now() - datetime.timedelta(hours=10 - i)
        )
        users.append(u)

    assert send_batched_email_digests() == 2
    assert sorted(m.to[0] for m in mail.outbox) == [users[0].email, users[1].email]

    mail.outbox.clear()
    assert send_batched_email_digests() == 2
    assert sorted(m.to[0] for m in mail.outbox) == [users[2].email, users[3].email]


@pytest.mark.django_db
def test_a_crash_between_sending_and_settling_cannot_loop_forever(user):
    """The attempt is charged at claim time precisely so that a worker dying
    after the send — a deploy, an OOM kill — costs at most MAX_RETRY_ATTEMPTS
    duplicates instead of one every BATCH_CLAIM_TIMEOUT for ever."""
    fail(user, BATCH_SIZE_TRIGGER)

    def die_after_sending(*args, **kwargs):
        # Stands in for the process disappearing: the mail is gone, the rows are
        # never settled, the claim is left behind.
        raise SystemExit("killed mid-sweep")

    for _ in range(MAX_RETRY_ATTEMPTS + 2):
        with (
            patch("apps.notifications.engine._send_digest_email", side_effect=die_after_sending),
            contextlib.suppress(SystemExit),
        ):
            send_batched_email_digests()
        # The claim is orphaned; time passes and it becomes reclaimable.
        NotificationDelivery.objects.filter(batch_claimed_at__isnull=False).update(
            batch_claimed_at=timezone.now() - BATCH_CLAIM_TIMEOUT - datetime.timedelta(minutes=1)
        )

    rows = NotificationDelivery.objects.filter(batch_queued_at__isnull=False)
    assert all(r.attempts <= MAX_RETRY_ATTEMPTS for r in rows)
    assert not rows.filter(status=DeliveryStatus.PENDING).exists(), "spent rows must leave the queue"

    # And the queue is now genuinely empty, not merely quiet.
    mail.outbox.clear()
    assert send_batched_email_digests() == 0
    assert mail.outbox == []


@pytest.mark.django_db
def test_unsubscribing_after_the_queue_cancels_the_pending_email(user):
    """Batching puts minutes between the decision to email and the email, and
    the user can withdraw consent in that gap. The promised unsubscribe has to
    apply to what is already queued, not just to what comes next."""
    fail(user, BATCH_SIZE_TRIGGER)
    assert NotificationDelivery.objects.filter(batch_queued_at__isnull=False).count() == BATCH_SIZE_TRIGGER

    NotificationPreference.objects.create(
        user=user, event_type=EventType.POST_FAILED, channel=Channel.EMAIL, is_enabled=False
    )

    assert send_batched_email_digests() == 0
    assert mail.outbox == []

    rows = NotificationDelivery.objects.filter(batch_queued_at__isnull=False)
    assert all(r.status == DeliveryStatus.FAILED for r in rows)
    assert all("turned this email off" in r.error_message for r in rows)


@pytest.mark.django_db
def test_turning_it_off_on_the_preferences_page_also_cancels_the_queue(user, client):
    """Cancelling only from the unsubscribe endpoint would miss every other way
    to turn the email off — the preferences page included."""
    fail(user, BATCH_SIZE_TRIGGER)

    client.force_login(user)
    client.post(reverse("notifications:preferences"), {})

    assert send_batched_email_digests() == 0
    assert mail.outbox == []
