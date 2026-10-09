"""Per-caller hourly call counters for the Agent API and MCP.

Every authenticated call increments one ``ApiKeyUsageHourly`` row, keyed by
caller, UTC hour, action and status. The rows serve two readers:

* the hourly and daily caps in ``apps.api.limits.enforce_usage_caps``, which
  need a count that survives deploys (the cache is per-process LocMem unless
  ``REDIS_URL`` is set, and is emptied by every restart);
* anyone asking "who is calling how much", including brightbean-analytics,
  which reads a few thousand of these rows a night instead of one audit row
  per call.

Whether a call *also* earns an ``ApiKeyAuditLog`` row is decided separately,
in ``apps.api.middleware``.

Calls are counted from ``log_audit_entry`` on their way out. The few that
return before reaching it are caught by ``CountUncountedApiCallsMiddleware``.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from django.db import connection
from django.db.models import Field, Q, Sum
from django.http import HttpRequest
from django.utils import timezone

from apps.api_keys.models import ApiKeyUsageHourly

logger = logging.getLogger(__name__)


def actor_for(api_key: Any) -> str:
    """The counter key for a caller: ``key:<uuid>`` or ``oauth:<user_id>``.

    ``OAuthMcpActor.id`` is already ``oauth:<user_id>``, namespaced so it can
    never collide with a real key's UUID.
    """
    if getattr(api_key, "is_oauth", False):
        return str(api_key.id)
    return f"key:{api_key.id}"


def hour_start(now: dt.datetime) -> dt.datetime:
    return now.astimezone(dt.UTC).replace(minute=0, second=0, microsecond=0)


def day_start(now: dt.datetime) -> dt.datetime:
    return hour_start(now).replace(hour=0)


def usage_in_windows(actor: str, now: dt.datetime) -> tuple[int, int]:
    """Calls this actor made in the current UTC hour and the current UTC day.

    429s are left out: a refused call did no work, and counting it would let
    a client that ignores ``Retry-After`` keep itself locked out of the next
    window by hammering this one.
    """
    this_hour = hour_start(now)
    totals = (
        ApiKeyUsageHourly.objects.filter(actor=actor, hour_start__gte=day_start(now))
        .exclude(status_code=429)
        .aggregate(hour=Sum("count", filter=Q(hour_start=this_hour)), day=Sum("count"))
    )
    return totals["hour"] or 0, totals["day"] or 0


def record_usage(request: HttpRequest, *, action: str, status_code: int) -> None:
    """Count one call against the caller's row for this hour.

    One upsert, so concurrent requests can't lose an increment the way a
    read-modify-write would. Best-effort like the audit row: a failure here
    must not fail the request it is counting.
    """
    api_key = getattr(request, "api_key", None)
    if api_key is None:
        return
    # Set before the write, so a failed upsert is not retried by the
    # catch-all below and counted twice.
    request._api_usage_counted = True  # type: ignore[attr-defined]
    is_oauth = getattr(api_key, "is_oauth", False)
    now = timezone.now()
    table = connection.ops.quote_name(ApiKeyUsageHourly._meta.db_table)
    count = connection.ops.quote_name("count")
    actor = actor_for(api_key)
    params = [
        actor,
        _db_value("hour_start", hour_start(now)),
        action[:64],
        status_code,
        _db_value("last_seen_at", now),
        _db_value("api_key", None if is_oauth else api_key.pk),
        _db_value("actor_user", getattr(api_key, "issued_by_id", None) if is_oauth else None),
        _db_value("workspace", getattr(api_key, "workspace_id", None)),
    ]
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} "
                f"(actor, hour_start, action, status_code, {count}, last_seen_at, api_key_id, actor_user_id, workspace_id) "
                "VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s) "
                "ON CONFLICT (actor, hour_start, workspace_id, action, status_code) "
                f"DO UPDATE SET {count} = {table}.{count} + 1, last_seen_at = excluded.last_seen_at",
                params,
            )
    except Exception:  # noqa: BLE001 — best-effort, swallow.
        logger.warning("Failed to record API usage for actor %s", actor, exc_info=True)


def _db_value(field_name: str, value: Any) -> Any:
    """Adapt a raw-SQL parameter the way the ORM would for this column.

    The upsert bypasses the ORM, and the backends disagree on wire formats:
    SQLite (the dev server) stores UUIDs as bare hex and datetimes as naive
    UTC strings, Postgres takes both natively.
    """
    if value is None:
        return None
    field = ApiKeyUsageHourly._meta.get_field(field_name)
    # Every name passed here is a concrete column, never a reverse relation.
    assert isinstance(field, Field)
    return field.get_db_prep_value(value, connection, prepared=False)


class CountUncountedApiCallsMiddleware:
    """Count authenticated API calls that finished without being counted.

    Nearly every call is counted by ``log_audit_entry``. A few return before
    it: an idempotent replay, an MCP body that isn't valid JSON-RPC, an
    unhandled 500. Uncounted, those would get past the hourly and daily caps
    without using any of the budget. Counting here is the backstop, so a
    route added later with its own early return is covered too.

    It only counts and never writes an audit row: those paths kept no row
    before, and a replay changed nothing.

    It acts after the view because that is the only point a real middleware
    can see ``request.api_key``: Ninja authenticates inside the view.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)
        if getattr(request, "api_key", None) is not None and not getattr(request, "_api_usage_counted", False):
            from apps.api.api import _action_for_path

            status_code = response.status_code
            action = _action_for_path(request.method or "GET", request.path or "", status_code=status_code)
            record_usage(request, action=action, status_code=status_code)
        return response
