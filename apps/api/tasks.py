"""Background tasks for the Agent API.

Today there is exactly one: a 24-hourly sweep that deletes stale
``IdempotencyRecord`` rows. The model docstring promises a 24h window
for replay; without an actual sweep, any row whose worker died between
``claim_idempotency_slot`` and ``finalize_idempotent_response`` /
``release_idempotent_claim`` lingers forever in the PENDING state,
locking the agent's retries with that key to HTTP 409.
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
