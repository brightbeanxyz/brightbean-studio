"""Derived analytics computations — engagement rate, period deltas.

These functions operate on already-fetched snapshot rows; they do not call
into any provider. The only "magic" is the engagement-rate formula, which
exactly mirrors the design's ``EngagementCard`` logic in
``analytics/varA.jsx``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .metrics import ENGAGEMENT_DENOMINATORS, ENGAGEMENT_PARTS, METRICS

# Kinds whose card value is our average of the daily figures, not a sum.
AVERAGED_KINDS = ("percent", "minutes")


@dataclass
class DerivedMetric:
    """The output shape every card / chart consumes."""

    value: float
    delta: float  # % change vs previous equal-length period
    # Daily values for the *current* period; ``None`` for a day with no
    # reported value yet (see ``_reported_days``), which charts draw as a gap.
    series: list[float | None]
    kind: str  # "count" | "percent" | "minutes"
    # How BrightBean produced ``value`` when the platform didn't report it as
    # shown. YouTube's developer policies allow metrics derived from API data
    # only when they are labelled as ours, so every card and the agent API key
    # their "calculated by BrightBean" labels off these fields.
    averaged: bool = False  # our average of the platform's daily figures
    estimated: bool = False  # built from other counts (per-post deltas, follower totals)
    # Ratios only: the metric key the value divides by ("followers" for the
    # follower-count fallback), or ``None`` when there was nothing to divide by.
    denominator: str | None = None


def calculate_engagement_rate(engagements: float, views: float | None = None, reach: float | None = None) -> float:
    denominator = 0.0
    if views and views > 0:
        denominator = float(views)
    elif reach and reach > 0:
        denominator = float(reach)
    if denominator <= 0:
        return 0.0
    return round((float(engagements) / denominator) * 100, 2)


def _split(values: list[float], days: int) -> tuple[list[float], list[float]]:
    """Return (current, previous) windows of ``days`` length, latest-last."""
    if not values:
        return [], []
    # values is assumed to already cover at least 2*days; if shorter, the
    # previous window may be empty (resulting in a zero-baseline delta).
    cur = values[-days:]
    prev = values[-2 * days : -days]
    return cur, prev


def _reported_days(present: list[bool], kind: str) -> list[bool]:
    """Which days count as reported, for both the value and the sparkline.

    For a rate (percent) a day without data has no value at all. For a daily
    quantity (count, minutes) a quiet day inside the window really is 0, but
    the days after the last report haven't arrived yet (YouTube Analytics
    lags 2-3 days), so only that trailing run is unreported.
    """
    if kind == "percent":
        return list(present)
    last = max((i for i, is_present in enumerate(present) if is_present), default=-1)
    return [i <= last for i in range(len(present))]


def _with_gaps(values: list[float], reported: list[bool] | None) -> list[float | None]:
    if reported is None:
        return [float(v) for v in values]
    return [float(v) if ok else None for v, ok in zip(values, reported, strict=False)]


def _window_value(values: list[float], present: list[bool] | None, kind: str) -> float:
    """Sum a window of counts, or average a window of percent / minutes.

    ``present`` marks the days that actually have a value; the series itself
    is zero-filled, so without it a day with no data yet would count as a real
    zero. Averages use only the days :func:`_reported_days` counts as reported.
    """
    if kind not in AVERAGED_KINDS:
        return float(sum(values))
    if present is not None:
        values = [v for v, ok in zip(values, _reported_days(present, kind), strict=False) if ok]
    return sum(values) / len(values) if values else 0.0


def derive(
    values_by_day: list[float],
    days: int,
    kind: str,
    *,
    present: list[bool] | None = None,
    estimated: bool = False,
) -> DerivedMetric:
    """Reduce a daily series into the value + delta + sparkline a card needs.

    For counts, the value is the SUM over the window. For percent / minutes,
    the value is the AVERAGE of the days with data (a rate that's already
    daily — summing would be meaningless). ``present`` is the per-day "has
    data" mask aligned with ``values_by_day``; ``estimated`` marks a series we
    built ourselves rather than read from the platform.
    """
    cur, prev = _split(values_by_day, days)
    cur_present, prev_present = _split(present, days) if present is not None else (None, None)
    cur_val = _window_value(cur, cur_present, kind)
    prev_val = _window_value(prev, prev_present, kind)
    delta = ((cur_val - prev_val) / prev_val) * 100 if prev_val else 0.0
    return DerivedMetric(
        value=cur_val,
        delta=round(delta, 1),
        series=_with_gaps(cur, _reported_days(cur_present, kind) if cur_present is not None else None),
        kind=kind,
        averaged=kind in AVERAGED_KINDS,
        estimated=estimated,
    )


def engagement_rate(
    series_by_metric: dict[str, list[float]],
    days: int,
    fallback_followers: int = 0,
    *,
    present_by_metric: dict[str, list[bool]] | None = None,
) -> DerivedMetric:
    """Compute derived engagement rate per the design's formula.

    rate = (sum of engagement parts over period) / denom * 100

    Where denom is the first of ``ENGAGEMENT_DENOMINATORS`` with data in the
    current window (summed over the same period), falling back to
    ``fallback_followers``. The result's ``denominator`` names which one was
    used, so the card can show the formula it was actually calculated with.

    The sparkline is per-day with the same denominator: ``sum(parts_day_i) /
    denom_day_i * 100``, or ``/ fallback_followers`` on the follower fallback.
    With ``present_by_metric``, days after the last report of the metrics it
    divides are ``None`` (not reported yet) rather than a plunge to 0%.
    """
    parts_keys = [k for k in series_by_metric if k in ENGAGEMENT_PARTS]
    denom_key = next(
        (d for d in ENGAGEMENT_DENOMINATORS if d in series_by_metric and sum(series_by_metric.get(d, [])[-days:]) > 0),
        None,
    )

    # Keep the full 2*days window through ``_split`` so the previous-period
    # numerator and denominator are both populated for the delta calc. The
    # sparkline (current period only) is sliced off the tail at the end.
    parts_series_per_day = []
    if parts_keys:
        aligned = [series_by_metric[k][-2 * days :] for k in parts_keys]
        max_len = max((len(s) for s in aligned), default=0)
        aligned = [s + [0.0] * (max_len - len(s)) for s in aligned]
        parts_series_per_day = [sum(day_values) for day_values in zip(*aligned, strict=False)]

    parts_cur, parts_prev = _split(parts_series_per_day, days)
    parts_cur_window = parts_series_per_day[-days:]
    if denom_key:
        denom_series_per_day = list(series_by_metric[denom_key])[-2 * days :]
        denom_cur_total = sum(denom_series_per_day[-days:])
        denom_prev_total = sum(denom_series_per_day[-2 * days : -days])
        denom_cur_window = denom_series_per_day[-days:]
        # Right-align with the parts window; a shorter series has no early days.
        denom_cur_window = [0.0] * (len(parts_cur_window) - len(denom_cur_window)) + denom_cur_window
        denominator = denom_key
    else:
        denom_cur_total = float(fallback_followers)
        denom_prev_total = float(fallback_followers)
        denom_cur_window = [float(fallback_followers)] * len(parts_cur_window)
        denominator = "followers" if fallback_followers > 0 else None

    rate_cur = (sum(parts_cur) / denom_cur_total) * 100 if denom_cur_total > 0 else 0.0
    rate_prev = (sum(parts_prev) / denom_prev_total) * 100 if denom_prev_total > 0 else 0.0
    delta = ((rate_cur - rate_prev) / rate_prev) * 100 if rate_prev else 0.0

    # Sparkline = CURRENT window only.
    sparkline: list[float | None] = [
        (part / denom) * 100 if denom > 0 else 0.0
        for part, denom in zip(parts_cur_window, denom_cur_window[-len(parts_cur_window) :], strict=False)
    ]
    if present_by_metric is not None and sparkline:
        # A rate is reported once what it divides is: the denominator, or on
        # the follower fallback any of the parts.
        basis = [denom_key] if denom_key else parts_keys
        masks = [present_by_metric[k][-days:] for k in basis if k in present_by_metric]
        if masks:
            present = [any(day) for day in zip(*masks, strict=False)]
            present = [False] * (len(sparkline) - len(present)) + present
            reported = _reported_days(present[-len(sparkline) :], "count")
            sparkline = [v if ok else None for v, ok in zip(sparkline, reported, strict=False)]

    return DerivedMetric(
        value=round(rate_cur, 2),
        delta=round(delta, 1),
        series=sparkline,
        kind="percent",
        denominator=denominator,
    )


def kind_of(metric_key: str) -> str:
    return METRICS.get(metric_key, {}).get("kind", "count")


def labelled(metrics: Iterable[str]) -> list[tuple[str, str]]:
    """Pair metric keys with their display labels for template iteration."""
    return [(m, METRICS.get(m, {}).get("label", m.title())) for m in metrics]
