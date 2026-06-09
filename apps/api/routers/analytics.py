"""``/api/v1/analytics/*`` — read-only channel and post analytics.

Designed for the agent polling workflow: an agent schedules a post via
``/api/v1/posts``, waits for it to publish, then iteratively calls these
endpoints to observe how it performs.

Both routes:

1. Enforce HTTP rate limits (per-key, per-workspace, global) up front.
2. Require the ``view_analytics`` workspace permission — analytics is a
   separately-scoped capability in the permission registry, so a key
   that wasn't granted it can't read performance data even for accounts
   it's otherwise allowlisted on.
3. Re-use the same allowlist guards (``_resolve_account`` /
   ``_get_workspace_post``) as ``/api/v1/posts``, so a partial-scope key
   can't read analytics for accounts it can't already see.
4. Delegate the actual response assembly to
   ``apps.analytics.api_builders`` so MCP and REST stay byte-equal.
5. Write a success audit log on the way out.

Failure paths produce ``analytics.read.{status_code}`` audit rows via the
centralised handler in ``apps/api/api.py``.
"""

from __future__ import annotations

import uuid

from ninja import Query, Router

from apps.analytics.api_builders import build_account_analytics, build_post_analytics
from apps.api.limits import enforce_http_rate_limits
from apps.api.middleware import log_audit_entry
from apps.api.routers.posts import _get_workspace_post, _require_perm, _resolve_account
from apps.api.schemas import AccountAnalyticsResponse, PostAnalyticsResponse

router = Router(tags=["analytics"])


@router.get(
    "/accounts/{account_id}",
    response=AccountAnalyticsResponse,
    summary="Read channel analytics summary",
)
def account_analytics(
    request,
    account_id: uuid.UUID,
    days: int = Query(
        30,
        ge=7,
        le=90,
        description=(
            "Rolling window size in days. Must be between 7 and 90 inclusive. "
            "The ``derive`` helper needs 2× this many days of snapshots to "
            "compute the period-over-period delta, so the cap keeps DB scans bounded."
        ),
    ),
):
    enforce_http_rate_limits(request, is_write=False)
    _require_perm(request, "view_analytics")
    account = _resolve_account(request, account_id)
    log_audit_entry(
        request,
        action="analytics.read.account",
        target_id=account.id,
        status_code=200,
    )
    return build_account_analytics(account, days)


@router.get(
    "/posts/{post_id}",
    response=PostAnalyticsResponse,
    summary="Read post analytics with per-platform metrics",
)
def post_analytics(request, post_id: uuid.UUID):
    enforce_http_rate_limits(request, is_write=False)
    _require_perm(request, "view_analytics")
    post = _get_workspace_post(request, post_id)
    log_audit_entry(
        request,
        action="analytics.read.post",
        target_id=post.id,
        status_code=200,
    )
    return build_post_analytics(post)
