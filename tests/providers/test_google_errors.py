"""Boundary behaviour of :func:`next_google_quota_reset`.

The answer lands in ``QuotaExceededError.resets_at``, which the publisher turns
into ``retry_at`` and the analytics sync into "blocked until". A reset moment
that had already elapsed would therefore release a blocked account straight back
onto an API still refusing it, so the invariant worth pinning is absolute rather
than approximate: the result is *strictly* after ``now``, in the second the
boundary passes as much as in any other.

Both UTC offsets are exercised because Pacific midnight moves: 08:00 UTC under
PST, 07:00 under PDT. A test written only in summer would pass all winter while
checking nothing about the hour it claims to check.
"""

import os
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfoNotFoundError

import pytest

from providers.google_errors import next_google_quota_reset

# Midnight US/Pacific, expressed in UTC, on a winter and a summer date.
PST_RESET = datetime(2026, 1, 15, 8, 0, tzinfo=UTC)
PDT_RESET = datetime(2026, 9, 17, 7, 0, tzinfo=UTC)

# The two 2026 DST switches, as UTC instants: 02:00 local on each transition
# day, plus that day's own midnight boundary.
SPRING_FORWARD_MIDNIGHT = datetime(2026, 3, 8, 8, 0, tzinfo=UTC)
SPRING_FORWARD_SWITCH = datetime(2026, 3, 8, 10, 0, tzinfo=UTC)
FALL_BACK_MIDNIGHT = datetime(2026, 11, 1, 7, 0, tzinfo=UTC)
FALL_BACK_SWITCH = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)

ONE_DAY = timedelta(days=1)
ONE_SECOND = timedelta(seconds=1)


def _sweep_strictly_future(around: datetime, *, radius: timedelta = timedelta(minutes=2)) -> None:
    """Assert the invariant at every second in ``around`` ± ``radius``.

    Swept rather than spot-checked because the failure mode is a single unlucky
    second, and a coarser step walks straight over it.
    """
    now = around - radius
    end = around + radius
    while now <= end:
        result = next_google_quota_reset(now)
        assert result > now, f"{result.isoformat()} is not after {now.isoformat()}"
        now += ONE_SECOND


@contextmanager
def _host_timezone(name: str):
    """Run the block with the process clock in ``name``.

    Without this the naive-input cases below are vacuous on a UTC host — which
    is what CI is, and precisely where a local-time misreading would hide.
    """
    previous = os.environ.get("TZ")
    os.environ["TZ"] = name
    time.tzset()
    try:
        yield
    finally:
        if previous is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = previous
        time.tzset()


def _without_tzdata():
    """Stand in for a slim image whose ``ZoneInfo`` lookup finds nothing."""
    return patch(
        "providers.google_errors.ZoneInfo",
        side_effect=ZoneInfoNotFoundError("No time zone found with key America/Los_Angeles"),
    )


@pytest.mark.parametrize("reset", [PST_RESET, PDT_RESET], ids=["PST", "PDT"])
class TestResetBoundary:
    """The three instants around a boundary, in both UTC offsets."""

    def test_just_before_the_boundary_returns_that_boundary(self, reset):
        assert next_google_quota_reset(reset - ONE_SECOND) == reset

    def test_standing_exactly_on_the_boundary_rolls_to_tomorrow(self, reset):
        """``next`` means next: the reset underfoot is spent, not upcoming."""
        assert next_google_quota_reset(reset) == reset + ONE_DAY

    def test_just_after_the_boundary_rolls_to_tomorrow(self, reset):
        """The minute after the daily reset must not hand back an elapsed moment.

        Getting this wrong would read as "quota is spent until 07:00" with 07:00
        already behind us — a cooldown whose deadline has expired on arrival.
        """
        assert next_google_quota_reset(reset + ONE_SECOND) == reset + ONE_DAY

    def test_never_returns_an_elapsed_moment_around_the_boundary(self, reset):
        _sweep_strictly_future(reset)


class TestDaylightSavingHandover:
    """Pacific midnight keeps its wall clock; its UTC hour is what shifts."""

    def test_reset_moves_an_hour_earlier_in_utc_when_pdt_begins(self):
        # 2026-03-08 springs forward at 02:00, so that day's own midnight is
        # still PST (08:00 UTC) while the one after it is PDT (07:00 UTC).
        last_pst_day = datetime(2026, 3, 7, 12, tzinfo=UTC)
        first_pdt_day = datetime(2026, 3, 8, 12, tzinfo=UTC)

        assert next_google_quota_reset(last_pst_day) == datetime(2026, 3, 8, 8, 0, tzinfo=UTC)
        assert next_google_quota_reset(first_pdt_day) == datetime(2026, 3, 9, 7, 0, tzinfo=UTC)

    def test_reset_moves_an_hour_later_in_utc_when_pst_returns(self):
        # 2026-11-01 falls back at 02:00: that day's midnight is still PDT
        # (07:00 UTC), the one after it PST (08:00 UTC).
        last_pdt_day = datetime(2026, 10, 31, 12, tzinfo=UTC)
        first_pst_day = datetime(2026, 11, 1, 12, tzinfo=UTC)

        assert next_google_quota_reset(last_pdt_day) == datetime(2026, 11, 1, 7, 0, tzinfo=UTC)
        assert next_google_quota_reset(first_pst_day) == datetime(2026, 11, 2, 8, 0, tzinfo=UTC)

    @pytest.mark.parametrize(
        "instant",
        [SPRING_FORWARD_MIDNIGHT, SPRING_FORWARD_SWITCH, FALL_BACK_MIDNIGHT, FALL_BACK_SWITCH],
        ids=["spring-midnight", "spring-switch", "fall-midnight", "fall-switch"],
    )
    def test_a_23_or_25_hour_local_day_stays_in_the_future(self, instant):
        """Both the midnight boundary and the switch itself, second by second."""
        _sweep_strictly_future(instant)


class TestNaiveInput:
    """A naive ``now`` means UTC, never the host's zone.

    Read as local time it would be silently shifted by the host offset, and on
    any machine east of Greenwich that shift is enough to hand back a reset
    moment the caller has already passed.
    """

    NAIVE_NOW = datetime(2026, 9, 17, 7, 0, 29)

    def test_naive_now_matches_the_same_instant_spelled_as_utc(self):
        with _host_timezone("Europe/Berlin"):
            assert next_google_quota_reset(self.NAIVE_NOW) == next_google_quota_reset(
                self.NAIVE_NOW.replace(tzinfo=UTC)
            )

    def test_naive_now_is_still_strictly_future(self):
        # Host-local reading returns 07:00:00 UTC here — 29 seconds behind the
        # caller's own clock, and indistinguishable from the boundary bug.
        with _host_timezone("Europe/Berlin"):
            result = next_google_quota_reset(self.NAIVE_NOW)

        assert result > self.NAIVE_NOW.replace(tzinfo=UTC)
        assert result == datetime(2026, 9, 18, 7, 0, tzinfo=UTC)

    def test_naive_now_west_of_greenwich_too(self):
        """The mirror case: a westward host shifts it the other way."""
        with _host_timezone("America/New_York"):
            result = next_google_quota_reset(self.NAIVE_NOW)

        assert result > self.NAIVE_NOW.replace(tzinfo=UTC)
        assert result == datetime(2026, 9, 18, 7, 0, tzinfo=UTC)

    def test_naive_now_does_not_crash_the_tzdata_fallback(self):
        """``_next_utc_hour`` compared against ``now`` — naive input raised."""
        with _without_tzdata():
            result = next_google_quota_reset(self.NAIVE_NOW)

        assert result == datetime(2026, 9, 17, 8, 0, tzinfo=UTC)


class TestMissingTimeZoneDatabase:
    """Slim images ship without tzdata; a missing zone degrades, never raises."""

    def test_falls_back_to_the_fixed_utc_hour(self):
        with _without_tzdata():
            result = next_google_quota_reset(datetime(2026, 9, 17, 7, 0, 1, tzinfo=UTC))

        # 08:00 rather than 07:00: without the zone, assume the later (PST) hour.
        assert result == datetime(2026, 9, 17, 8, 0, tzinfo=UTC)

    def test_fallback_is_strictly_future_on_its_own_boundary(self):
        boundary = datetime(2026, 9, 17, 8, 0, tzinfo=UTC)

        with _without_tzdata():
            assert next_google_quota_reset(boundary) == boundary + ONE_DAY
