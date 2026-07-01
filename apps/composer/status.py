"""Post status aggregation helpers.

Editorial status lives on ``PlatformPost`` — each social account flows through
the workflow independently. ``Post.status`` is a *derived* property computed
from its children. This module holds the pure aggregation function so it can
be reused by model properties, views, and tests.
"""

# Canonical workflow order from least- to most-advanced. "Lower" states win
# when a post has mixed children in non-terminal states so the UI reflects the
# most conservative / action-required state.
_WORKFLOW_ORDER = [
    "draft",
    "changes_requested",
    "rejected",
    # A client-requested hold is action-required, so it ranks low (wins over
    # approved/scheduled) — a partially-held post surfaces as "on_hold" rather
    # than letting an un-held sibling mask it at the Post level.
    "on_hold",
    "pending_review",
    "pending_client",
    "approved",
    "scheduled",
    "publishing",
    "partially_published",
    "published",
]

# Statuses considered "terminal publishing outcomes".
_TERMINAL = {"published", "failed"}


def derive_post_status(statuses):
    """Return an aggregate post-level status from an iterable of child statuses.

    Rules:
      - empty → "draft"
      - all children share the same value → that value
      - all terminal, all published → "published"
      - all terminal, all failed → "failed"
      - all terminal, mix of published/failed → "partially_published"
      - any child failed + any non-terminal → "publishing" (still in flight)
      - otherwise → the "lowest" (earliest in _WORKFLOW_ORDER) child status.
        This means e.g. (draft, scheduled) → "draft", (scheduled, publishing) →
        "scheduled", (pending_review, approved) → "pending_review".
    """
    values = [s for s in statuses if s]
    if not values:
        return "draft"

    unique = set(values)
    if len(unique) == 1:
        return values[0]

    # All terminal: combine by outcome.
    if unique <= (_TERMINAL | {"failed"}):
        if "published" in unique and "failed" in unique:
            return "partially_published"
        if unique == {"published"}:
            return "published"
        return "failed"

    # Otherwise return the "lowest" state by workflow order. Unknown values fall
    # to the end so a weird stray status doesn't shadow real ones.
    def _rank(s):
        try:
            return _WORKFLOW_ORDER.index(s)
        except ValueError:
            return len(_WORKFLOW_ORDER)

    result = min(unique, key=_rank)
    # A client hold ranks low so it surfaces over approved/scheduled siblings, but
    # it must not shadow a channel that has already published — report the partial
    # outcome instead of hiding "published" behind "on_hold".
    if result == "on_hold" and "published" in unique:
        return "partially_published"
    return result
