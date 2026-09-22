"""The recurring sweeps are actually scheduled.

Worth asserting because the failure is silent: ``notify()`` deliberately does
not send email for the batched events, so if ``send_batched_email_digests`` is
never registered, publish-failure mail simply stops and nothing logs an error.
"""

import pytest
from background_task.models import Task

from apps.common.tasks import COUNTER_PURGE_INTERVAL_SECONDS
from apps.notifications.tasks import (
    NOTIFICATION_BATCH_INTERVAL_SECONDS,
    NOTIFICATION_RETRY_INTERVAL_SECONDS,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "repeat"),
    [
        ("retry_failed_deliveries", NOTIFICATION_RETRY_INTERVAL_SECONDS),
        ("send_batched_email_digests", NOTIFICATION_BATCH_INTERVAL_SECONDS),
        ("purge_email_counters", COUNTER_PURGE_INTERVAL_SECONDS),
    ],
)
def test_the_sweep_is_registered_to_repeat(name, repeat):
    """post_migrate registers these, and the test database has been migrated."""
    task = Task.objects.filter(verbose_name=name).first()
    assert task is not None, f"{name} was never registered — it would never run"
    assert task.repeat == repeat


@pytest.mark.django_db
def test_registration_is_idempotent():
    """It runs on every migrate; a second pass must not queue a duplicate."""
    from apps.notifications.apps import NotificationsConfig

    NotificationsConfig._register_tasks(sender=None)

    assert Task.objects.filter(verbose_name="send_batched_email_digests").count() == 1
