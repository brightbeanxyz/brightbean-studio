"""Background tasks: on-connect backfill + scheduled incremental sync.

Both run inside the existing ``process_tasks`` worker (no new infra).

Cadence (per the plan's "How new metrics get pulled" section):
  * Account-level metrics            → once per day per account
  * Posts < 24h old                  → hourly
  * Posts 1–7 days old               → every 6 hours
  * Posts 7–30 days old              → daily
  * Posts 30–90 days old             → weekly
  * Posts > 90 days old              → stop
"""

from __future__ import annotations

import logging
from datetime import date as dt_date
from datetime import timedelta

from background_task import background
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Per-platform backfill window (days) on initial connect.
BACKFILL_DAYS_PER_PLATFORM: dict[str, int] = {
    "facebook": 90,
    "instagram": 90,
    "instagram_login": 90,
    "linkedin_personal": 90,
    "linkedin_company": 90,
    "youtube": 90,
    "pinterest": 90,
    "threads": 90,
    "google_business": 90,
    "tiktok": 60,
    # Bluesky / Mastodon have no analytics surface — skip.
    "bluesky": 0,
    "mastodon": 0,
}
DEFAULT_BACKFILL_DAYS = 90


# ---------------------------------------------------------------------------
# PostMetrics / AccountMetrics → snapshot rows
# ---------------------------------------------------------------------------

# Per-platform overrides for ``PostMetrics`` field → catalog metric_key.
# A missing platform entry uses the identity mapping (impressions→impressions,
# etc.) augmented with ``video_views``→``views``. Each provider stuffs its
# native fields into different ``PostMetrics`` slots — these overrides realign
# them with the keys the UI queries from ``PLATFORM_METRICS``.
_POST_FIELD_OVERRIDES: dict[str, dict[str, str]] = {
    "threads": {
        # providers/threads.py:419-423 stuffs views/replies/reposts into the
        # impressions/comments/shares dataclass fields.
        "impressions": "views",
        "comments": "replies",
        "shares": "reposts",
    },
    "linkedin_company": {
        # providers/linkedin.py:580-585 returns likeCount/shareCount; catalog
        # for linkedin_company uses 'reactions' and 'reposts'.
        "likes": "reactions",
        "shares": "reposts",
    },
    "mastodon": {
        # providers/mastodon.py:313-316: favourites→likes (ok), reblogs→shares,
        # replies→comments. Catalog wants reposts/replies.
        "shares": "reposts",
        "comments": "replies",
    },
    "bluesky": {
        # AT Protocol counts: align with the bluesky catalog.
        "shares": "reposts",
        "comments": "replies",
    },
}

# Per-platform overrides for ``PostMetrics.extra[key]`` → catalog metric_key.
# Generic ``extra`` keys recognized by the default code path are listed in
# ``_GENERIC_POST_EXTRA_KEYS`` below; per-platform overrides handle the
# vocabulary that providers actually use.
_POST_EXTRA_OVERRIDES: dict[str, dict[str, str]] = {
    "pinterest": {
        # providers/pinterest.py:328 stores Pinterest's OUTBOUND_CLICK under
        # ``outbound_clicks`` in extra; the catalog metric key is ``outbound``.
        "outbound_clicks": "outbound",
    },
}

_GENERIC_POST_EXTRA_KEYS = (
    "reactions",
    "replies",
    "reposts",
    "outbound",
    "watch_time",
    "avg_view_pct",
)


def _post_metrics_to_dict(metrics, platform: str) -> dict[str, float]:
    """Flatten ``providers.types.PostMetrics`` into ``{metric_key: value}``.

    Uses per-platform overrides so each provider's idiosyncratic field choices
    (Threads stuffing views into ``impressions``, LinkedIn returning likeCount
    where the catalog uses ``reactions``, …) land under the keys the UI queries.

    Unset (zero) fields are omitted so we don't pin zeros into snapshots for
    metrics the platform didn't return.
    """
    field_overrides = _POST_FIELD_OVERRIDES.get(platform, {})
    extra_overrides = _POST_EXTRA_OVERRIDES.get(platform, {})

    out: dict[str, float] = {}
    base_map = (
        ("impressions", "impressions"),
        ("reach", "reach"),
        ("likes", "likes"),
        ("comments", "comments"),
        ("shares", "shares"),
        ("saves", "saves"),
        ("clicks", "clicks"),
        ("video_views", "views"),
    )
    for src, default_key in base_map:
        v = getattr(metrics, src, 0) or 0
        if v:
            key = field_overrides.get(src, default_key)
            out[key] = float(v)

    extra = getattr(metrics, "extra", {}) or {}
    # Generic extras that match the catalog key exactly.
    for key in _GENERIC_POST_EXTRA_KEYS:
        v = extra.get(key)
        if v is not None:
            try:
                out[key] = float(v)
            except (TypeError, ValueError):
                pass
    # Per-platform extras (e.g. Pinterest ``outbound_clicks`` → ``outbound``).
    for src_key, dest_key in extra_overrides.items():
        v = extra.get(src_key)
        if v is not None:
            try:
                out[dest_key] = float(v)
            except (TypeError, ValueError):
                pass
    return out


def _account_metrics_to_dict(metrics, platform: str) -> dict[str, float]:
    """Flatten ``AccountMetrics`` into ``{metric_key: value}``.

    ``platform`` is reserved for future per-platform tweaks (Facebook stashes
    page_engaged_users in the ``reach`` field, etc.) but currently no platform
    overrides are needed for the implemented account-level metrics. Kept
    symmetric with ``_post_metrics_to_dict``.
    """
    del platform  # currently unused but reserved
    out: dict[str, float] = {}
    for src, key in (
        ("impressions", "impressions"),
        ("reach", "reach"),
        ("profile_views", "profile_visits"),
    ):
        v = getattr(metrics, src, 0) or 0
        if v:
            out[key] = float(v)
    # followers_gained = daily new follows; catalog calls it ``follows`` for
    # most platforms (and ``subscribers`` for YouTube — promoted from extra).
    gained = getattr(metrics, "followers_gained", 0) or 0
    if gained:
        out["follows"] = float(gained)
    extra = getattr(metrics, "extra", {}) or {}
    for key in ("views", "watch_time", "subscribers", "likes", "comments", "shares"):
        v = extra.get(key)
        if v is not None:
            try:
                out[key] = float(v)
            except (TypeError, ValueError):
                pass
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_provider(account):
    """Mirror apps.social_accounts.tasks.check_social_account_health's credential
    resolution so platforms with org-level creds (Meta apps, etc.) work."""
    from apps.credentials.models import PlatformCredential
    from providers import get_provider

    credentials: dict = {}
    try:
        org_id = account.workspace.organization_id
        cred = PlatformCredential.objects.for_org(org_id).get(platform=account.platform, is_configured=True)
        credentials = cred.credentials
    except PlatformCredential.DoesNotExist:
        env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
        credentials = env_creds.get(account.platform, {})

    if account.platform == "mastodon" and account.instance_url:
        from apps.social_accounts.models import MastodonAppRegistration

        try:
            reg = MastodonAppRegistration.objects.get(instance_url=account.instance_url)
            credentials = {
                **credentials,
                "instance_url": account.instance_url,
                "client_id": reg.client_id,
                "client_secret": reg.client_secret,
            }
        except MastodonAppRegistration.DoesNotExist:
            pass
    return get_provider(account.platform, credentials)


def _is_insufficient_scope(exc: Exception) -> bool:
    """Best-effort recognition of "you don't have the right scope" errors.

    Each provider raises slightly different exceptions; rather than wire
    them all up here, sniff the message for the common signals.
    """
    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in (
            "scope",
            "permission",
            "insufficient",
            "forbidden",
            "(#10)",  # Meta's permission-error subcode
            "(#200)",  # Meta's permission-denied subcode
        )
    )


def _write_account_snapshot(account, metric_values: dict[str, float], on_date: dt_date) -> int:
    from .models import AccountInsightsSnapshot

    if not metric_values:
        return 0
    count = 0
    for key, value in metric_values.items():
        AccountInsightsSnapshot.objects.update_or_create(
            social_account=account,
            metric_key=key,
            date=on_date,
            defaults={"value": value},
        )
        count += 1
    return count


def _write_post_snapshot(post, metric_values: dict[str, float], on_date: dt_date) -> int:
    from .models import PostInsightsSnapshot

    if not metric_values:
        return 0
    count = 0
    for key, value in metric_values.items():
        PostInsightsSnapshot.objects.update_or_create(
            platform_post=post,
            metric_key=key,
            date=on_date,
            defaults={"value": value},
        )
        count += 1
    return count


# ---------------------------------------------------------------------------
# Per-account work
# ---------------------------------------------------------------------------


def _sync_account_metrics(account, on_date: dt_date) -> None:
    """Fetch today's account-level metrics and write one snapshot row per metric."""
    from datetime import datetime, time

    provider = _resolve_provider(account)
    start = datetime.combine(on_date, time.min, tzinfo=timezone.get_current_timezone())
    end = datetime.combine(on_date, time.max, tzinfo=timezone.get_current_timezone())
    try:
        metrics = provider.get_account_metrics(account.oauth_access_token, (start, end))
    except NotImplementedError:
        return
    except Exception as exc:
        if _is_insufficient_scope(exc):
            _mark_needs_reconnect(account)
        logger.warning("get_account_metrics failed for %s: %s", account, exc)
        return
    _write_account_snapshot(account, _account_metrics_to_dict(metrics, account.platform), on_date)


def _sync_post_metrics(post, on_date: dt_date) -> None:
    """Fetch this post's current metrics and write today's snapshot rows."""
    account = post.social_account
    provider = _resolve_provider(account)
    try:
        metrics = provider.get_post_metrics(account.oauth_access_token, post.platform_post_id)
    except NotImplementedError:
        return
    except Exception as exc:
        if _is_insufficient_scope(exc):
            _mark_needs_reconnect(account)
        logger.warning("get_post_metrics failed for post %s (%s): %s", post.id, account.platform, exc)
        return
    _write_post_snapshot(post, _post_metrics_to_dict(metrics, account.platform), on_date)


def _mark_needs_reconnect(account):
    if account.analytics_needs_reconnect:
        return
    account.analytics_needs_reconnect = True
    account.save(update_fields=["analytics_needs_reconnect", "updated_at"])


def _post_cadence_due(post, now=None) -> bool:
    """Decide whether ``post`` is due for a new sync per the decay schedule."""
    from .models import PostInsightsSnapshot

    now = now or timezone.now()
    if not post.published_at:
        return False
    age = now - post.published_at
    if age > timedelta(days=90):
        return False
    if age < timedelta(days=1):
        cadence = timedelta(hours=1)
    elif age < timedelta(days=7):
        cadence = timedelta(hours=6)
    elif age < timedelta(days=30):
        cadence = timedelta(days=1)
    else:
        cadence = timedelta(days=7)
    last = (
        PostInsightsSnapshot.objects.filter(platform_post=post)
        .order_by("-captured_at")
        .values_list("captured_at", flat=True)
        .first()
    )
    if last is None:
        return True
    return (now - last) >= cadence


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------


@background(schedule=0)
def backfill_account_analytics(account_id: str, days: int | None = None) -> None:
    """One-shot backfill on account connect / reconnect.

    Account-level: writes today's row (the only one we can reliably get
    without provider time-series support — full historical backfill is
    deferred until we extend providers to return daily series).

    Per-post: for every published post within the platform's window, fetch
    its current cumulative metrics and write today's snapshot rows.
    """
    from apps.composer.models import PlatformPost
    from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount

    try:
        account = SocialAccount.objects.get(id=account_id)
    except SocialAccount.DoesNotExist:
        return
    enabled = set(AnalyticsPlatformConfig.enabled_platforms())
    if account.platform not in enabled:
        return
    cap = BACKFILL_DAYS_PER_PLATFORM.get(account.platform, DEFAULT_BACKFILL_DAYS)
    if cap == 0:
        return
    days = min(days or cap, cap)
    today = timezone.now().date()
    cutoff = timezone.now() - timedelta(days=days)

    _sync_account_metrics(account, today)

    posts = PlatformPost.objects.filter(
        social_account=account,
        status=PlatformPost.Status.PUBLISHED,
        published_at__gte=cutoff,
    ).exclude(platform_post_id="")
    for post in posts:
        with transaction.atomic():
            _sync_post_metrics(post, today)


@background(schedule=0)
def sync_all_account_analytics() -> None:
    """Hourly cron: refresh enabled accounts on the decay-by-age schedule."""
    from apps.composer.models import PlatformPost
    from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount

    enabled = set(AnalyticsPlatformConfig.enabled_platforms())
    if not enabled:
        return
    today = timezone.now().date()

    accounts = SocialAccount.objects.filter(
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        platform__in=enabled,
    ).select_related("workspace")
    from .models import AccountInsightsSnapshot

    for account in accounts:
        # Account-level: at most once per day per account. Skip if today's
        # row already exists so an hourly cron doesn't turn into 24 API calls.
        if not AccountInsightsSnapshot.objects.filter(social_account=account, date=today).exists():
            _sync_account_metrics(account, today)

        # Per-post: only those whose cadence window has elapsed
        cap_days = BACKFILL_DAYS_PER_PLATFORM.get(account.platform, DEFAULT_BACKFILL_DAYS)
        if cap_days == 0:
            continue
        cutoff = timezone.now() - timedelta(days=cap_days)
        posts = PlatformPost.objects.filter(
            social_account=account,
            status=PlatformPost.Status.PUBLISHED,
            published_at__gte=cutoff,
        ).exclude(platform_post_id="")
        for post in posts:
            if _post_cadence_due(post):
                _sync_post_metrics(post, today)
