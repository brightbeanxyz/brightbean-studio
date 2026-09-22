"""QuietHours.digest_mode routes a user's notification email into the batch queue.

Regression: digest_mode was a user-facing toggle ("Daily digest" on the
preferences page) that nothing read. Its only consumer, `tasks.send_daily_digests`,
was never registered on a schedule, so switching it on did nothing — and had that
task ever been scheduled it would have sent a digest *on top of* the immediate
emails, because it read straight off the Notification table with no delivery
bookkeeping and could not tell what had already gone out.

digest_mode now queues email on the same delivery-row queue the batched event
types use, delivered once a day at DAILY_DIGEST_HOUR in the user's own timezone.
"""

import datetime
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.engine import (
    BATCH_SIZE_TRIGGER,
    BATCH_WINDOW_MINUTES,
    DAILY_DIGEST_HOUR,
    notify,
    send_batched_email_digests,
)
from apps.notifications.models import (
    Channel,
    DeliveryStatus,
    EventType,
    NotificationDelivery,
    NotificationPreference,
    QuietHours,
)

# Email on by default and NOT in BATCHED_EMAIL_EVENTS, so a normal user gets it
# immediately — which is what makes it prove digest_mode captured it.
IMMEDIATE_EMAIL_EVENT = EventType.POST_CHANGES_REQUESTED
OTHER_IMMEDIATE_EMAIL_EVENT = EventType.SOCIAL_ACCOUNT_DISCONNECTED
# In BATCHED_EMAIL_EVENTS, so it queues on the short window for everyone.
ROLLING_BATCH_EVENT = EventType.POST_FAILED
# Batched *and* non-critical, so quiet hours would otherwise drop it before it
# could ever reach a digest.
QUIET_HOURS_DROPPABLE_EVENT = EventType.REPORT_GENERATED


def at(hour, minute=0, day=17):
    """A fixed UTC moment, so clock-anchored assertions don't depend on the clock."""
    return datetime.datetime(2026, 9, day, hour, minute, tzinfo=datetime.UTC)


@contextmanager
def frozen_now(moment):
    with patch("django.utils.timezone.now", return_value=moment):
        yield


def email_deliveries(user):
    return NotificationDelivery.objects.filter(notification__user=user, channel=Channel.EMAIL)


def queued_at(user, moment):
    email_deliveries(user).filter(batch_queued_at__isnull=False).update(batch_queued_at=moment)


def make_user(suffix, *, digest_mode=False, tz="UTC"):
    user = User.objects.create_user(
        email=f"{suffix}@example.com", password="testpass123", name=suffix, tos_accepted_at=timezone.now()
    )
    if digest_mode:
        QuietHours.objects.create(user=user, digest_mode=True, timezone=tz)
    return user


@pytest.mark.django_db
class TestDigestModeUser:
    def test_gets_one_daily_email_and_no_immediate_ones(self, user, mailoutbox):
        QuietHours.objects.create(user=user, digest_mode=True)

        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        notify(user, OTHER_IMMEDIATE_EMAIL_EVENT, "Account disconnected")
        notify(user, EventType.TEAM_MEMBER_INVITED, "You were invited")

        # Nothing inline: the queued row IS the delivery, not an extra copy.
        assert mailoutbox == []
        assert email_deliveries(user).count() == 3
        assert all(d.batch_queued_at is not None for d in email_deliveries(user))

        queued_at(user, at(6))

        with frozen_now(at(DAILY_DIGEST_HOUR - 1)):
            assert send_batched_email_digests() == 0
        assert mailoutbox == []

        with frozen_now(at(DAILY_DIGEST_HOUR + 1)):
            assert send_batched_email_digests() == 1

        # ONE email, covering every event type rather than one per type.
        assert len(mailoutbox) == 1
        sent = mailoutbox[0]
        assert sent.to == [user.email]
        assert "daily digest" in sent.subject.lower()
        assert "Changes requested" in sent.body
        assert "Account disconnected" in sent.body
        assert "You were invited" in sent.body
        assert set(email_deliveries(user).values_list("status", flat=True)) == {DeliveryStatus.DELIVERED}

        with frozen_now(at(DAILY_DIGEST_HOUR + 2)):
            assert send_batched_email_digests() == 0
        assert len(mailoutbox) == 1

    def test_send_time_is_anchored_to_the_clock_not_the_queue(self, user, mailoutbox):
        """Queueing after the send hour waits for tomorrow, it does not drag it."""
        QuietHours.objects.create(user=user, digest_mode=True)
        notify(user, IMMEDIATE_EMAIL_EVENT, "Queued after today's send hour")
        queued_at(user, at(DAILY_DIGEST_HOUR + 4))

        with frozen_now(at(DAILY_DIGEST_HOUR + 5)):
            assert send_batched_email_digests() == 0

        with frozen_now(at(DAILY_DIGEST_HOUR, day=18)):
            assert send_batched_email_digests() == 1
        assert len(mailoutbox) == 1

    def test_send_hour_follows_the_users_timezone(self, mailoutbox):
        # 08:00 in New York is 12:00 UTC in September (EDT).
        ny_user = make_user("newyork", digest_mode=True, tz="America/New_York")
        notify(ny_user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        queued_at(ny_user, at(2))

        with frozen_now(at(9)):  # 05:00 in New York
            assert send_batched_email_digests() == 0

        with frozen_now(at(13)):  # 09:00 in New York
            assert send_batched_email_digests() == 1
        assert len(mailoutbox) == 1

    def test_size_trigger_does_not_force_the_digest_early(self, user, mailoutbox):
        """A busy day must not ship "today's digest" before the send hour."""
        QuietHours.objects.create(user=user, digest_mode=True)
        for i in range(BATCH_SIZE_TRIGGER + 2):
            notify(user, IMMEDIATE_EMAIL_EVENT, f"Changes requested {i}")
        queued_at(user, at(DAILY_DIGEST_HOUR + 1))

        # Well past the size trigger, but today's send hour has already gone by
        # and these were queued after it.
        with frozen_now(at(DAILY_DIGEST_HOUR + 2)):
            assert send_batched_email_digests() == 0
        assert mailoutbox == []

    def test_per_event_opt_out_still_wins(self, user, mailoutbox):
        """Turning email off for one event beats digest_mode turning it on."""
        QuietHours.objects.create(user=user, digest_mode=True)
        NotificationPreference.objects.create(
            user=user, event_type=IMMEDIATE_EMAIL_EVENT, channel=Channel.EMAIL, is_enabled=False
        )

        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        notify(user, EventType.POST_REJECTED, "Post rejected")

        # Opted out at notify() time: it never becomes an email delivery at all.
        assert not email_deliveries(user).filter(notification__event_type=IMMEDIATE_EMAIL_EVENT).exists()

        queued_at(user, at(6))
        with frozen_now(at(DAILY_DIGEST_HOUR + 1)):
            assert send_batched_email_digests() == 1

        assert len(mailoutbox) == 1
        assert "Post rejected" in mailoutbox[0].body
        assert "Changes requested" not in mailoutbox[0].body

    def test_opting_out_after_queueing_drops_only_that_event(self, user, mailoutbox):
        """A digest spans types, so one being switched off must not cancel the rest."""
        QuietHours.objects.create(user=user, digest_mode=True)
        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        notify(user, EventType.POST_REJECTED, "Post rejected")
        queued_at(user, at(6))

        # Withdrawn in the gap between queueing and sending.
        NotificationPreference.objects.create(
            user=user, event_type=IMMEDIATE_EMAIL_EVENT, channel=Channel.EMAIL, is_enabled=False
        )

        with frozen_now(at(DAILY_DIGEST_HOUR + 1)):
            assert send_batched_email_digests() == 1

        assert len(mailoutbox) == 1
        assert "Post rejected" in mailoutbox[0].body
        assert "Changes requested" not in mailoutbox[0].body

        cancelled = email_deliveries(user).get(notification__event_type=IMMEDIATE_EMAIL_EVENT)
        assert cancelled.status == DeliveryStatus.FAILED
        delivered = email_deliveries(user).get(notification__event_type=EventType.POST_REJECTED)
        assert delivered.status == DeliveryStatus.DELIVERED

    def test_quiet_hours_defers_into_the_digest_instead_of_dropping(self, user, mailoutbox):
        """Suppressing a digest user's email would lose it, not silence it."""
        QuietHours.objects.create(
            user=user,
            is_enabled=True,
            start_time=datetime.time(0, 0),
            end_time=datetime.time(23, 59),
            timezone="UTC",
            digest_mode=True,
        )

        notify(user, QUIET_HOURS_DROPPABLE_EVENT, "Report ready")

        assert mailoutbox == []
        assert email_deliveries(user).count() == 1

        queued_at(user, at(6))
        with frozen_now(at(DAILY_DIGEST_HOUR + 1)):
            assert send_batched_email_digests() == 1
        assert "Report ready" in mailoutbox[0].body

    def test_quiet_hours_still_suppresses_a_digest_users_webhook(self, user):
        """Only the queued email is exempt — a webhook fires immediately."""
        QuietHours.objects.create(
            user=user,
            is_enabled=True,
            start_time=datetime.time(0, 0),
            end_time=datetime.time(23, 59),
            timezone="UTC",
            digest_mode=True,
        )
        NotificationPreference.objects.create(
            user=user, event_type=QUIET_HOURS_DROPPABLE_EVENT, channel=Channel.WEBHOOK, is_enabled=True
        )

        with patch("apps.notifications.engine._dispatch_webhook") as dispatch_webhook:
            notify(user, QUIET_HOURS_DROPPABLE_EVENT, "Report ready", data={"webhook_url": "https://hooks.test/x"})

        dispatch_webhook.assert_not_called()
        assert not NotificationDelivery.objects.filter(notification__user=user, channel=Channel.WEBHOOK).exists()
        assert email_deliveries(user).count() == 1


@pytest.mark.django_db
class TestEveryoneElseIsUnaffected:
    def test_immediate_email_still_goes_out_immediately(self, user, mailoutbox):
        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")

        assert len(mailoutbox) == 1
        delivery = email_deliveries(user).get()
        assert delivery.batch_queued_at is None
        assert delivery.status == DeliveryStatus.DELIVERED
        assert send_batched_email_digests() == 0

    def test_digest_mode_off_explicitly_is_also_unaffected(self, user, mailoutbox):
        QuietHours.objects.create(user=user, digest_mode=False)
        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")

        assert len(mailoutbox) == 1
        assert email_deliveries(user).get().batch_queued_at is None

    def test_quiet_hours_still_suppresses_non_critical_email(self, user, mailoutbox):
        QuietHours.objects.create(
            user=user,
            is_enabled=True,
            start_time=datetime.time(0, 0),
            end_time=datetime.time(23, 59),
            timezone="UTC",
        )
        notify(user, QUIET_HOURS_DROPPABLE_EVENT, "Report ready")

        assert mailoutbox == []
        assert not email_deliveries(user).exists()

    def test_the_rolling_batch_is_untouched(self, user, mailoutbox):
        notify(user, ROLLING_BATCH_EVENT, "Post failed")

        assert mailoutbox == []
        assert send_batched_email_digests() == 0

        email_deliveries(user).update(
            batch_queued_at=timezone.now() - datetime.timedelta(minutes=BATCH_WINDOW_MINUTES + 1)
        )
        assert send_batched_email_digests() == 1
        assert len(mailoutbox) == 1
        assert "Post failed" in mailoutbox[0].body

    def test_a_waiting_digest_user_does_not_starve_the_rolling_batch(self, user, mailoutbox):
        """The two populations must not share one oldest-first candidate window.

        Digest rows sit queued for hours and rolling rows for minutes, so a
        shared query would sort every digest row first and never reach these.
        """
        waiting = make_user("waiting", digest_mode=True)
        notify(waiting, IMMEDIATE_EMAIL_EVENT, "not due yet")
        queued_at(waiting, at(DAILY_DIGEST_HOUR + 1))

        notify(user, ROLLING_BATCH_EVENT, "should go out now")
        queued_at(user, at(DAILY_DIGEST_HOUR + 1) - datetime.timedelta(minutes=BATCH_WINDOW_MINUTES + 1))

        with frozen_now(at(DAILY_DIGEST_HOUR + 2)):
            assert send_batched_email_digests() == 1

        assert len(mailoutbox) == 1
        assert "should go out now" in mailoutbox[0].body


@pytest.mark.django_db
class TestDeactivatedRecipients:
    """Batching puts a day between queueing and sending; accounts close in that gap.

    notify() already refuses to create anything for an inactive user, so this is
    only reachable by deactivating someone whose email is already queued — which
    is exactly what the deleted send_daily_digests guarded against with its
    `if not user.is_active: continue`.
    """

    def test_a_daily_digest_is_not_sent_to_a_deactivated_recipient(self, user, mailoutbox):
        QuietHours.objects.create(user=user, digest_mode=True)
        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        queued_at(user, at(6))

        user.is_active = False
        user.save(update_fields=["is_active"])

        with frozen_now(at(DAILY_DIGEST_HOUR + 1)):
            assert send_batched_email_digests() == 0

        assert mailoutbox == []
        delivery = email_deliveries(user).get()
        assert delivery.status == DeliveryStatus.FAILED
        assert "deactivated" in delivery.error_message
        # Retired, not left PENDING: a stranded row is invisible to every later
        # sweep and nothing would ever clear it.
        assert delivery.batch_claimed_at is None

    def test_a_rolling_batch_is_not_sent_to_a_deactivated_recipient(self, user, mailoutbox):
        """Same guard, shared by both sweeps rather than bolted onto the daily one."""
        notify(user, ROLLING_BATCH_EVENT, "Post failed")
        email_deliveries(user).update(
            batch_queued_at=timezone.now() - datetime.timedelta(minutes=BATCH_WINDOW_MINUTES + 1)
        )

        user.is_active = False
        user.save(update_fields=["is_active"])

        assert send_batched_email_digests() == 0
        assert mailoutbox == []
        assert email_deliveries(user).get().status == DeliveryStatus.FAILED

    def test_reactivating_before_the_send_hour_still_delivers(self, user, mailoutbox):
        """The guard is a live check, not a one-way door."""
        QuietHours.objects.create(user=user, digest_mode=True)
        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        queued_at(user, at(6))

        assert email_deliveries(user).get().status == DeliveryStatus.PENDING

        with frozen_now(at(DAILY_DIGEST_HOUR + 1)):
            assert send_batched_email_digests() == 1
        assert len(mailoutbox) == 1


@pytest.mark.django_db
class TestDailyDigestUnsubscribe:
    """A daily digest spans every event type, so its link cannot name one."""

    def test_the_digest_carries_a_one_click_unsubscribe_link(self, user, mailoutbox):
        QuietHours.objects.create(user=user, digest_mode=True)
        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        queued_at(user, at(6))

        with frozen_now(at(DAILY_DIGEST_HOUR + 1)):
            assert send_batched_email_digests() == 1

        headers = mailoutbox[0].extra_headers
        assert "List-Unsubscribe" in headers
        assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"

    def test_unsubscribing_from_it_turns_off_all_notification_email(self, client, user):
        """The only honest reading of "unsubscribe" on an email collecting every type."""
        from apps.notifications.unsubscribe import ALL_EVENTS, make_token

        response = client.post(f"/notifications/unsubscribe/{make_token(user.pk, ALL_EVENTS)}/")
        assert response.status_code == 200

        off = set(
            NotificationPreference.objects.filter(user=user, channel=Channel.EMAIL, is_enabled=False).values_list(
                "event_type", flat=True
            )
        )
        assert off == set(EventType.values)

        # And it actually stops the mail: nothing queues afterwards.
        QuietHours.objects.create(user=user, digest_mode=True)
        notify(user, IMMEDIATE_EMAIL_EVENT, "Changes requested")
        assert not email_deliveries(user).exists()

    def test_a_get_does_not_unsubscribe_anyone(self, client, user):
        """Link prefetchers must not switch someone's email off — same as per-event."""
        from apps.notifications.unsubscribe import ALL_EVENTS, make_token

        response = client.get(f"/notifications/unsubscribe/{make_token(user.pk, ALL_EVENTS)}/")
        assert response.status_code == 200
        assert not NotificationPreference.objects.filter(user=user, is_enabled=False).exists()


@pytest.mark.django_db
def test_there_is_only_one_digest_implementation():
    """Guards the double-send this change removed.

    `send_daily_digests` read notifications straight off the Notification table
    with no delivery bookkeeping, so it could not tell what had already been
    emailed. Scheduling it alongside the immediate path was the bug.
    """
    from apps.notifications import tasks

    assert not hasattr(tasks, "send_daily_digests")
    assert hasattr(tasks, "send_batched_email_digests")
