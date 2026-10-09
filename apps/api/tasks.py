"""Background tasks for the Agent API.

Two sweeps:

* An hourly one that deletes stale ``IdempotencyRecord`` rows. The model
  docstring promises a 24h window for replay; without an actual sweep, any
  row whose worker died between ``claim_idempotency_slot`` and
  ``finalize_idempotent_response`` / ``release_idempotent_claim`` lingers
  forever in the PENDING state, locking the agent's retries with that key to
  HTTP 409.
* A daily one that ages out ``ApiKeyAuditLog`` and ``ApiKeyUsageHourly``
  rows past their retention.
"""

from __future__ import annotations

import datetime as dt
import logging

from background_task import background
from django.utils import timezone

logger = logging.getLogger(__name__)


#: Rows older than this are eligible for deletion. Matches the value the
#: model docstring already promises ("we cache the first response under
#: (api_key, key) and replay it verbatim on subsequent matching requests
#: for 24 hours").
IDEMPOTENCY_RECORD_TTL_HOURS = 24

#: Sweep interval. The window only needs to be granular enough that no
#: stuck PENDING row persists more than a few minutes past its TTL.
SWEEP_INTERVAL_SECONDS = 60 * 60  # 1h


@background(schedule=0)
def sweep_stale_idempotency_records():
    """Delete ``IdempotencyRecord`` rows older than the TTL.

    Runs hourly via ``django-background-tasks``; the per-iteration cost
    is one indexed DELETE because ``created_at`` is indexed in the
    initial migration. Two things to call out:

    * We delete on ``created_at < cutoff`` regardless of
      ``response_status``. PENDING placeholders past their TTL are the
      thing we most want gone (they're the lock-stuck-retries failure
      mode); finalized rows past their TTL are simply expired replay
      cache and gain us nothing further.
    * Failure to run this task does NOT corrupt anything; it only
      means stale rows accumulate. The 24h replay contract is
      maintained as long as the sweep eventually runs.
    """
    from apps.api.models import IdempotencyRecord

    cutoff = timezone.now() - dt.timedelta(hours=IDEMPOTENCY_RECORD_TTL_HOURS)
    deleted, _ = IdempotencyRecord.objects.filter(created_at__lt=cutoff).delete()
    if deleted:
        logger.info("Swept %d stale IdempotencyRecord rows older than %s", deleted, cutoff)


#: Matches the ``org.audit_log_retention_days`` default in
#: ``apps/settings_manager/defaults.py``. Usage counters are kept as long: they
#: are a few dozen rows per key per day, and a year of them answers
#: year-on-year questions the audit rows no longer can.
AUDIT_LOG_RETENTION_DAYS = 365
USAGE_RETENTION_DAYS = 365

USAGE_SWEEP_INTERVAL_SECONDS = 24 * 60 * 60

#: Rows per DELETE. Keeps each statement short so the sweep never holds a lock
#: the request path's inserts have to wait on.
_SWEEP_CHUNK = 10_000


@background(schedule=0)
def sweep_api_usage_records():
    """Delete audit rows and usage counters older than their retention.

    Exceptions are swallowed for the same reason as ``purge_email_counters``:
    django-background-tasks drops a task that keeps raising, and losing the
    schedule is worse than one missed night.
    """
    from apps.api_keys.models import ApiKeyAuditLog, ApiKeyUsageHourly

    now = timezone.now()
    try:
        audit = _delete_in_chunks(
            ApiKeyAuditLog.objects.filter(created_at__lt=now - dt.timedelta(days=AUDIT_LOG_RETENTION_DAYS))
        )
        usage = _delete_in_chunks(
            ApiKeyUsageHourly.objects.filter(hour_start__lt=now - dt.timedelta(days=USAGE_RETENTION_DAYS))
        )
    except Exception:
        logger.exception("API usage sweep failed")
        return
    if audit or usage:
        logger.info("Swept %d audit row(s) and %d usage counter row(s) past retention", audit, usage)


def _delete_in_chunks(queryset) -> int:
    deleted = 0
    while pks := list(queryset.values_list("pk", flat=True)[:_SWEEP_CHUNK]):
        count, _ = queryset.model.objects.filter(pk__in=pks).delete()
        deleted += count
    return deleted
