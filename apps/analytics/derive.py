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


@dataclass
class DerivedMetric:
    """The output shape every card / chart consumes."""

    value: float
    delta: float  # % change vs previous equal-length period
    series: list[float]  # daily values for the *current* period
    kind: str  # "count" | "percent" | "minutes"


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


def derive(values_by_day: list[float], days: int, kind: str) -> DerivedMetric:
    """Reduce a daily series into the value + delta + sparkline a card needs.

    For counts, the value is the SUM over the window. For percent / minutes,
    the value is the AVERAGE (a rate that's already daily — summing would
    be meaningless).
    """
    cur, prev = _split(values_by_day, days)
    if kind in ("percent", "minutes"):
        cur_val = sum(cur) / len(cur) if cur else 0.0
        prev_val = sum(prev) / len(prev) if prev else 0.0
    else:
        cur_val = float(sum(cur))
        prev_val = float(sum(prev))
    delta = ((cur_val - prev_val) / prev_val) * 100 if prev_val else 0.0
    return DerivedMetric(
        value=cur_val,
        delta=round(delta, 1),
        series=[float(v) for v in cur],
        kind=kind,
    )


def engagement_rate(
    series_by_metric: dict[str, list[float]],
    days: int,
    fallback_followers: int = 0,
) -> DerivedMetric:
    """Compute derived engagement rate per the design's formula.

    rate = (sum of engagement parts over period) / denom * 100

    Where denom is the first available of ``reach, impressions, views, plays``
    (summed over the same period), falling back to ``fallback_followers``.

    The sparkline is per-day: ``sum(parts_day_i) / denom_day_i * 100`` when a
    daily denom is available; otherwise the daily numerator only.
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

    denom_series_by_metric = {d: list(series_by_metric.get(d, []))[-2 * days :] for d in ENGAGEMENT_DENOMINATORS}
    denom_series_per_day = list(series_by_metric.get(denom_key, []))[-2 * days :] if denom_key else []

    parts_cur, parts_prev = _split(parts_series_per_day, days)
    if denom_key:
        denom_cur_total = sum(denom_series_per_day[-days:])
        denom_prev_total = sum(denom_series_per_day[-2 * days : -days])
    else:
        denom_cur_total = float(fallback_followers)
        denom_prev_total = float(fallback_followers)

    rate_cur = (sum(parts_cur) / denom_cur_total) * 100 if denom_cur_total > 0 else 0.0
    rate_prev = (sum(parts_prev) / denom_prev_total) * 100 if denom_prev_total > 0 else 0.0
    delta = ((rate_cur - rate_prev) / rate_prev) * 100 if rate_prev else 0.0

    # Sparkline = CURRENT window only.
    parts_cur_window = parts_series_per_day[-days:]
    denom_cur_windows = {key: values[-days:] for key, values in denom_series_by_metric.items() if values}
    if denom_cur_windows:

        def daily_denominator(index: int) -> float:
            return next(
                (values[index] for values in denom_cur_windows.values() if index < len(values) and values[index] > 0),
                0.0,
            )

        sparkline = [
            (parts_cur_window[i] / daily_denominator(i)) * 100 if daily_denominator(i) > 0 else 0.0
            for i in range(len(parts_cur_window))
        ]
    else:
        sparkline = parts_cur_window

    return DerivedMetric(
        value=round(rate_cur, 2),
        delta=round(delta, 1),
        series=sparkline,
        kind="percent",
    )


def kind_of(metric_key: str) -> str:
    return METRICS.get(metric_key, {}).get("kind", "count")


def labelled(metrics: Iterable[str]) -> list[tuple[str, str]]:
    """Pair metric keys with their display labels for template iteration."""
    return [(m, METRICS.get(m, {}).get("label", m.title())) for m in metrics]
