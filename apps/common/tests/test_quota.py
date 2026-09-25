"""The shared quota breaker's alerting behaviour.

The breaker's mechanics (idempotency, the per-run cache, expiry) are exercised
through its callers in ``apps/analytics/tests/test_tasks.py`` and
``apps/inbox/tests/test_sync.py``. What is tested here is the part no caller
can assert for itself: whether a block is loud enough for anyone to notice.

That distinction is the whole reason this file exists. A spent daily budget
means a platform is gone for the rest of the day — analytics, the inbox and
reconnecting included — and the first time it happened nobody found out until a
user wrote in. A five-minute throttle is the breaker doing its job. Logging
both identically means either the daily case is missed or the throttle case
trains everyone to ignore it.
"""

import logging
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.common.quota import (
    credential_key,
    quota_blocked_until,
    read_scope,
    scopes_for,
    trip_from_exception,
    trip_quota_block,
)
from providers.exceptions import QuotaExceededError
from providers.youtube import API_BASE, UPLOAD_BASE, YouTubeProvider


class TestCredentialKey:
    def test_the_same_client_gets_the_same_key(self):
        """Accounts sharing an OAuth client share a budget, so they must share a row."""
        assert credential_key({"client_id": "abc"}) == credential_key({"client_id": "abc"})

    def test_different_clients_do_not_collide(self):
        assert credential_key({"client_id": "abc"}) != credential_key({"client_id": "xyz"})

    def test_the_key_does_not_contain_the_client_id(self):
        """It lands in the database and in logs; the client_id must not."""
        assert "abc" not in credential_key({"client_id": "abc"})

    @pytest.mark.parametrize("credentials", [None, {}, {"client_id": ""}])
    def test_unresolvable_credentials_share_one_key(self, credentials):
        assert credential_key(credentials) == "unknown"


@pytest.mark.django_db
class TestBlockAlerting:
    def test_a_spent_daily_budget_logs_at_error(self, caplog):
        """ERROR is what reaches Sentry, and a lost day is worth an event."""
        with caplog.at_level(logging.WARNING, logger="apps.common.quota"):
            trip_quota_block(
                "youtube",
                credential_key({"client_id": "c"}),
                "data",
                until=timezone.now() + timedelta(hours=9),
                reason="daily quota exhausted",
            )

        assert [r.levelno for r in caplog.records] == [logging.ERROR]

    def test_a_short_throttle_stays_a_warning(self, caplog):
        """Paging someone for a five-minute cooldown is how alerts get ignored."""
        with caplog.at_level(logging.WARNING, logger="apps.common.quota"):
            trip_quota_block(
                "youtube",
                credential_key({"client_id": "c"}),
                "data",
                until=timezone.now() + timedelta(minutes=5),
                reason="request rate throttled",
            )

        assert [r.levelno for r in caplog.records] == [logging.WARNING]

    def test_a_later_shorter_block_cannot_shorten_a_longer_one(self, caplog):
        """A throttle arriving mid-exhaustion must not wave the platform back in."""
        key = credential_key({"client_id": "c"})
        long_until = timezone.now() + timedelta(hours=9)
        trip_quota_block("youtube", key, "data", until=long_until, reason="daily quota exhausted")

        trip_quota_block(
            "youtube",
            key,
            "data",
            until=timezone.now() + timedelta(minutes=5),
            reason="request rate throttled",
        )

        assert quota_blocked_until("youtube", key, "data") == long_until
        from apps.analytics.models import ProviderQuotaBlock

        assert ProviderQuotaBlock.objects.get(platform="youtube", credential_key=key, quota_scope="data").reason == (
            "daily quota exhausted"
        )


@pytest.mark.django_db
class TestOneBreakerAcrossCallers:
    """The whole point of this module living in ``apps.common``.

    Three callers draw on the same per-client budget — the analytics sync, the
    inbox poll and the health check. Each used to resolve the scope its own
    way, and for every platform that meters a single pool they disagreed: the
    inbox wrote ``"data"`` while analytics looked up ``""``. Neither saw the
    other's block, so both kept calling an API that had already refused.
    """

    @pytest.mark.parametrize("platform", ["youtube", "tiktok", "linkedin"])
    def test_a_block_written_by_one_reader_is_seen_by_the_other(self, platform):
        key = credential_key({"client_id": "shared"})
        trip_quota_block(
            platform,
            key,
            read_scope(platform),
            until=timezone.now() + timedelta(hours=4),
            reason="spent",
        )

        assert quota_blocked_until(platform, key, read_scope(platform)) is not None

    def test_a_single_pool_platform_uses_the_empty_scope(self):
        """ "" is not a missing value — it is that platform's only budget."""
        assert read_scope("tiktok") == ""
        assert scopes_for("tiktok") == ("", "")

    def test_youtube_keeps_its_two_budgets_apart(self):
        """Blocking the cheap Data read because Analytics ran dry throws away the good half."""
        account_scope, post_scope = scopes_for("youtube")
        assert (account_scope, post_scope) == ("analytics", "data")

        key = credential_key({"client_id": "shared"})
        trip_quota_block(
            "youtube", key, account_scope, until=timezone.now() + timedelta(hours=4), reason="analytics spent"
        )

        assert quota_blocked_until("youtube", key, account_scope) is not None
        assert quota_blocked_until("youtube", key, post_scope) is None


@pytest.mark.django_db
class TestTripFromException:
    def test_it_reads_the_window_and_budget_off_the_exception(self):
        resets_at = timezone.now() + timedelta(hours=9)
        exc = QuotaExceededError("spent", resets_at=resets_at, quota_scope="data", status_code=403)
        key = credential_key({"client_id": "shared"})

        trip_from_exception("youtube", key, exc)

        assert quota_blocked_until("youtube", key, "data") == resets_at

    def test_a_platform_that_says_nothing_falls_back_to_its_read_scope(self):
        """The fallback the two hand-rolled copies disagreed on."""
        exc = QuotaExceededError("spent", status_code=403)
        key = credential_key({"client_id": "shared"})

        trip_from_exception("tiktok", key, exc)

        assert quota_blocked_until("tiktok", key, "") is not None

    def test_the_fallback_backoff_is_used_when_no_window_is_given(self):
        exc = QuotaExceededError("spent", status_code=403)
        key = credential_key({"client_id": "shared"})

        trip_from_exception("tiktok", key, exc, fallback_backoff=timedelta(hours=3))

        blocked = quota_blocked_until("tiktok", key, "")
        assert blocked > timezone.now() + timedelta(hours=2)


def _youtube_quota_refusal(url: str) -> QuotaExceededError:
    """The exception the real provider raises for a spent budget at ``url``.

    Built by the provider rather than by hand so these tests fail if its scope
    classification drifts, not only if the breaker's keying does.
    """
    body = {"error": {"code": 403, "errors": [{"reason": "quotaExceeded", "domain": "youtube.quota"}]}}
    response = MagicMock(status_code=403, url=url, headers={}, text="")
    response.json = MagicMock(return_value=body)
    exc = YouTubeProvider()._error_for_response(response)
    assert isinstance(exc, QuotaExceededError)
    return exc


@pytest.mark.django_db
class TestYouTubeUploadBucket:
    """Since June 2026 ``videos.insert`` has a bucket of its own: 100 calls a day.

    The regular 10,000-unit pool the inbox, analytics sync and health check
    share is a separate budget. Google refuses both with the same
    ``quotaExceeded`` body, so which one ran dry lives only in the scope the
    provider reads off the request — and a block filed under the wrong one
    stops, for the rest of the day, calls that still have budget.
    """

    def test_a_spent_upload_bucket_leaves_the_regular_pool_open(self):
        key = credential_key({"client_id": "shared"})
        exc = _youtube_quota_refusal(f"{UPLOAD_BASE}/videos?uploadType=resumable&part=snippet,status")

        trip_from_exception("youtube", key, exc)

        assert quota_blocked_until("youtube", key, "upload") is not None
        # Every scope the inbox, health check and analytics sync resolve.
        assert quota_blocked_until("youtube", key, read_scope("youtube")) is None
        for scope in scopes_for("youtube"):
            assert quota_blocked_until("youtube", key, scope) is None

    def test_a_spent_regular_pool_leaves_uploads_open(self):
        key = credential_key({"client_id": "shared"})
        exc = _youtube_quota_refusal(f"{API_BASE}/commentThreads?part=snippet,replies")

        trip_from_exception("youtube", key, exc)

        assert quota_blocked_until("youtube", key, read_scope("youtube")) is not None
        assert quota_blocked_until("youtube", key, "upload") is None

    def test_no_reader_resolves_to_the_upload_scope(self):
        """Nothing that polls or syncs may read the upload bucket's block."""
        assert "upload" not in scopes_for("youtube")
        assert read_scope("youtube") != "upload"
