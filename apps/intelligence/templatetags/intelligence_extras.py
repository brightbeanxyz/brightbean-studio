"""Template helpers for the Intelligence playground partials."""

from __future__ import annotations

from datetime import datetime

from django import template

register = template.Library()


@register.filter
def parse_iso_datetime(value):
    """Convert an ISO 8601 string from the Intelligence API into a
    ``datetime`` so Django's built-in ``|date`` filter can format it.

    Returns ``None`` for empty / unparseable input, callers should
    chain ``|default:""`` or wrap in ``{% if %}`` to handle absent
    dates.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # ``fromisoformat`` accepts ``+00:00`` offsets in Python 3.11+ and
        # accepts ``Z`` suffix in 3.11+. Normalize the trailing ``Z`` for
        # broader compatibility.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@register.filter
def humanize_slug(value):
    """Turn a snake_case slug into Title-cased display text.

    ``bold_claim`` → ``Bold claim``, ``pattern_interrupt`` →
    ``Pattern interrupt``. Falls back to ``str(value)`` for non-string
    inputs so callers don't need to null-check before piping.
    """
    if value is None:
        return ""
    text = str(value).replace("_", " ").replace("-", " ").strip()
    if not text:
        return ""
    return text[:1].upper() + text[1:]


@register.filter
def score_pct(value):
    """Convert a sub-score on the 0–10 axis into an integer percent for
    progress-bar widths in templates. Clamps to [0, 100] so a 12/10
    score doesn't overflow the bar visually."""
    try:
        pct = int(round(float(value) * 10))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, pct))


@register.filter
def humanize_count(value):
    """Format a big integer compactly: ``2_860_000`` → ``2.86M``,
    ``4650`` → ``4.65K``, ``431`` → ``431``. Falls back to
    ``str(value)`` on non-numerics. 0 renders as a dash (the API
    returns 0 for "unknown" on exemplar-channel subscriber counts).
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value) if value is not None else ""
    if n == 0:
        return ","
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.2f}K"
    return str(n)


@register.filter
def from_cents(value):
    """Convert an integer cent amount into a dollar string.

    ``1900`` → ``"19"``, ``9900`` → ``"99"``, ``9950`` → ``"99.50"``.
    Whole-dollar amounts render without trailing zeros so the price
    blocks stay compact on the pricing cards. Returns an empty string
    on non-numeric input rather than ``None``-y filter output.
    """
    try:
        cents = int(value)
    except (TypeError, ValueError):
        return ""
    dollars, rem = divmod(cents, 100)
    if rem == 0:
        return str(dollars)
    return f"{dollars}.{rem:02d}"


@register.filter
def pretty_percent(value, decimals=1):
    """Render a 0–1 float as ``XX.X%`` (default 1 decimal place).

    ``0.1229`` → ``12.3%``, ``0.0298`` → ``3.0%``, ``0`` → ``0.0%``.
    Returns an empty string for None / non-numerics so the template
    doesn't get noise like "None%". The ``decimals`` argument lets
    callers do ``{{ x|pretty_percent:0 }}`` for whole-number rendering.
    """
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return ""
    try:
        d = int(decimals)
    except (TypeError, ValueError):
        d = 1
    return f"{f * 100:.{max(0, d)}f}%"
