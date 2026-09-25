"""Template filters/tags for the analytics page.

Three jobs:
  - format metric values (counts → 1.2k / 3.4M, percent → 4.6%, minutes → 46.3h)
  - format delta badges (signed, no zero sign)
  - render an inline-SVG sparkline from a daily series
"""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def fmt_metric(value, kind: str = "count") -> str:
    """Match the design's ``fmt.metric`` (analytics/charts.jsx)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0"
    if kind == "percent":
        return f"{v:.1f}%"
    if kind == "minutes":
        # minutes → "Xh" or "X.Ym" depending on magnitude
        if v >= 60:
            return f"{v / 60:.1f}h"
        return f"{v:.0f}m"
    # count
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.1f}k"
    return f"{int(round(v))}"


@register.filter
def fmt_signed(value) -> str:
    """Signed percentage delta with one decimal, no zero sign."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0%"
    if v == 0:
        return "0%"
    sign = "+" if v > 0 else "−"
    return f"{sign}{abs(v):.1f}%"


@register.simple_tag
def sparkline(values, color: str = "var(--primary)", width: int = 160, height: int = 36):
    """Render an inline SVG sparkline. ``values`` is a list of numbers.

    ``None`` is a day with no reported value yet: it keeps its horizontal slot
    but draws nothing, so unreported days read as a gap rather than a drop to 0.
    """
    vals = [None if v is None else float(v) for v in values or []]
    known = [v for v in vals if v is not None]
    if not known:
        return ""
    n = len(vals)
    vmin, vmax = min(known), max(known)
    rng = (vmax - vmin) or 1.0
    # Map each value to (x, y) within the viewBox, splitting at gaps.
    pad = 2
    inner_w = max(1, width - 2 * pad)
    inner_h = max(1, height - 2 * pad)
    segments: list[list[tuple[float, float]]] = [[]]
    for i, v in enumerate(vals):
        if v is None:
            if segments[-1]:
                segments.append([])
            continue
        x = pad + (i * inner_w / max(1, n - 1) if n > 1 else inner_w / 2)
        y = pad + inner_h - ((v - vmin) / rng) * inner_h
        segments[-1].append((x, y))
    lines, fills = [], []
    for pts in (seg for seg in segments if seg):
        # A lone point gets a hair-length stroke so its round cap shows as a dot.
        line = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        lines.append(line if len(pts) > 1 else f"{line} l0.01,0")
        fills.append(f"{line} L{pts[-1][0]:.1f},{height - pad} L{pts[0][0]:.1f},{height - pad} Z")
    path_d = " ".join(lines)
    fill_d = " ".join(fills)
    svg = (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'preserveAspectRatio="none" style="display:block">'
        f'<path d="{fill_d}" fill="{color}" fill-opacity="0.12" stroke="none"/>'
        f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f"</svg>"
    )
    return mark_safe(svg)


@register.filter
def delta_color(value) -> str:
    """Tailwind-style color name based on a positive/negative/zero delta."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "neutral"
    if v == 0:
        return "neutral"
    return "good" if v > 0 else "bad"


@register.filter
def get_item(d, key):
    """Look up a dict key in templates (works for stats[m] in tables)."""
    if d is None:
        return None
    try:
        return d.get(key)
    except AttributeError:
        return None


@register.filter
def get_stat(stats, metric_key) -> int | float:
    """Return ``stats[metric_key]`` or 0 — used in the All-posts table."""
    if not stats:
        return 0
    return stats.get(metric_key, 0)


@register.filter
def strip_leading_at(value) -> str:
    """Strip a single leading ``@`` from a handle, leaving in-string ``@`` intact.

    YouTube's ``customUrl`` arrives with a leading ``@`` already attached, and
    Mastodon-style ``user@instance.tld`` handles contain a meaningful in-string
    ``@``. The built-in ``|cut:"@"`` filter would corrupt the Mastodon form.
    """
    if value is None:
        return ""
    s = str(value)
    return s[1:] if s.startswith("@") else s
