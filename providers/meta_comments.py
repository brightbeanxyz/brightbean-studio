"""Comment reading shared by the two Instagram providers.

Both Instagram connections read the same ``/{media-id}/comments`` edge and
differ only in host — Facebook Login goes through ``graph.facebook.com``,
Instagram Login through ``graph.instagram.com``. Everything else (field sets,
cutoff arithmetic, the own-comment filter, the reply-target rules) is identical,
so it lives here once rather than being copy-pasted into both modules.

``FacebookProvider`` keeps its own versions: its comments edge answers with
``message`` rather than ``text``, its post ids need page-scoping first, and it
reads a ``/feed`` edge rather than ``/media``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from .types import InboxMessage

logger = logging.getLogger(__name__)

# Comment-poll bounds. The poll is a backstop for the ``comments`` webhook, so
# it trades completeness on very busy accounts for a predictable per-cycle cost:
# one media call plus at most INSTAGRAM_COMMENT_PAGE_LIMIT follow-ups per item.
INSTAGRAM_MEDIA_SCAN_LIMIT = 25
# Lower than Facebook's 50: with ``replies`` nested this is a three-level
# expansion, and Graph starts refusing large node counts outright.
INSTAGRAM_COMMENTS_PER_MEDIA = 25
INSTAGRAM_REPLIES_PER_COMMENT = 5
INSTAGRAM_COMMENT_PAGE_LIMIT = 4
# How far back the *media* scan reaches. Comments on older media are only
# reachable via the webhook.
INSTAGRAM_MEDIA_WINDOW_DAYS = 30
# Overlap applied to the caller's ``since``. The inbox passes the newest
# received_at across *all* message types for the account, so on an
# Instagram-Login account a DM that arrived after a comment would otherwise hide
# that comment forever. Re-fetching the overlap is free: _upsert_message only
# notifies on create.
INSTAGRAM_COMMENT_LOOKBACK_HOURS = 24

# One page is enough for reconciliation: it runs minutes after publishing, on a
# post whose only expected comment is ours.
INSTAGRAM_RECONCILE_COMMENT_LIMIT = 50

_ALWAYS_FIELDS = "id,text,timestamp,username"
_AUTHOR_FIELD = "from{id,username}"


def _field_set(*, author: bool, replies: bool) -> str:
    """Build one comment field set, with or without each optional part."""
    node = _ALWAYS_FIELDS + (f",{_AUTHOR_FIELD}" if author else "")
    if not replies:
        return node
    return f"{node},replies.limit({INSTAGRAM_REPLIES_PER_COMMENT}){{{node}}}"


# Graph fails the *whole* call on one unknown or unpermitted field, and ``from``
# and ``replies`` are the two most likely to be refused. Degrade them one axis
# at a time: dropping both together would lose every reply on an account that
# could read replies perfectly well and only objected to ``from``, and a
# customer answering our own first comment is exactly the message we cannot
# afford to lose.
#
# ``from`` is given up last because it carries the author id the own-comment
# filter prefers; ``username`` is requested at every level as the fallback
# signal, so even the final set can still recognise our own comments by handle.
INSTAGRAM_COMMENT_FIELD_SETS = (
    _field_set(author=True, replies=True),
    _field_set(author=True, replies=False),
    _field_set(author=False, replies=True),
    _field_set(author=False, replies=False),
)


def parse_graph_time(value: str | None) -> datetime | None:
    """Parse Graph's ``2026-08-07T12:34:56+0000`` timestamps.

    Always returns an aware datetime. A value without an offset would otherwise
    be compared against an aware cutoff (TypeError) and stored as a naive
    ``received_at``; Graph serves UTC, so assume it.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("+0000", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _comment_text(comment: dict) -> str:
    """Read a comment's body.

    Instagram's read edge spells it ``text`` while the write edge takes
    ``message``. Accept both: a response that ever used the write spelling would
    otherwise silently read as an empty comment, which for ``find_own_comment``
    means "not ours" and a duplicate on a live account.
    """
    return comment.get("text") or comment.get("message") or ""


def _comment_author(comment: dict) -> tuple[str, str]:
    """Return ``(author_id, author_username)`` for a comment, either possibly empty.

    Instagram withholds ``from`` on third-party comments in some app and
    permission combinations, returning only a bare ``username``, so both signals
    have to be read and neither can be required. The username is returned as
    Instagram spelled it — ``_same_handle`` normalizes for comparison, because a
    value normalized here would end up stored and displayed that way.
    """
    author = comment.get("from") or {}
    author_id = str(author.get("id") or "")
    return author_id, str(author.get("username") or comment.get("username") or "")


def _same_handle(left: str, right: str) -> bool:
    """Compare two Instagram handles, ignoring a leading @ and casing."""
    return bool(left and right and left.lstrip("@").lower() == right.lstrip("@").lower())


def _is_own_comment(author_id: str, author_handle: str, owner_id: str, owner_handle: str) -> bool:
    """True when the account itself wrote this comment.

    Checked on id *and* handle because either can be missing from the payload.
    An unrecognised own comment lands in the inbox as an inbound message from
    ourselves — including every first comment we post.
    """
    if owner_id and author_id and author_id == owner_id:
        return True
    return _same_handle(author_handle, owner_handle)


def find_own_instagram_comment(
    request,
    *,
    api_base: str,
    access_token: str,
    media_id: str,
    text: str,
    own_id: str,
    own_handle: str = "",
) -> str | None:
    """Return the id of a comment this account already left on ``media_id``.

    Reconciliation hook for retrying a first comment whose previous attempt
    failed: Instagram creates the comment before rejecting some malformed
    requests, so a blind retry double-comments.

    Errs toward reporting a match — a false positive costs one skipped comment,
    a false negative posts a duplicate on a live account, which cannot be taken
    back. So an author we cannot read at all counts as ours, and a read that
    fails propagates rather than answering "not there": the caller treats
    ``None`` as permission to post again.
    """
    resp = request(
        "GET",
        f"{api_base}/{media_id}/comments",
        access_token=access_token,
        params={"fields": "id,text,from", "limit": INSTAGRAM_RECONCILE_COMMENT_LIMIT},
    )

    for comment in resp.json().get("data", []):
        author_id, author_handle = _comment_author(comment)
        # Only skip on a *known* mismatch. An absent author is unreadable, not
        # foreign, and Instagram omits ``from`` on third-party comments.
        if (author_id or author_handle) and not _is_own_comment(author_id, author_handle, own_id, own_handle):
            continue
        if _comment_text(comment) == text:
            return str(comment.get("id") or "")
    return None


def resolve_comment_reply_target(comment_id: str, extra: dict | None = None) -> tuple[str, str]:
    """Return the ``(object_id, edge)`` a reply to this inbox item is posted to.

    Three cases:

    * A caption mention gives us only the media id, which has no ``replies``
      edge — that one is answered by commenting on the media itself.
    * A *reply* has no ``replies`` edge either. Instagram threads one level
      deep, so a reply is answered on its parent comment's edge; posting to the
      reply is rejected.
    * A top-level comment is answered on its own ``replies`` edge.

    A ``parent_id`` naming the media or the comment itself is not a parent
    comment — targeting it would publish a new top-level comment instead of a
    threaded reply — so it is ignored.
    """
    extra = extra or {}
    if extra.get("reply_edge") == "media":
        return str(comment_id), "comments"

    parent_id = str(extra.get("parent_id") or "")
    not_a_parent = {
        str(comment_id),
        str(extra.get("post_id") or ""),
        str(extra.get("stored_post_id") or ""),
        "",
    }
    if parent_id not in not_a_parent:
        return parent_id, "replies"
    return str(comment_id), "replies"


def fetch_instagram_comments(
    request,
    *,
    platform: str,
    host: str,
    media_url: str,
    access_token: str,
    since: datetime | None = None,
    owner_id: str = "",
    owner_handle: str = "",
) -> list[InboxMessage]:
    """Poll comments on the account's recent media.

    The ``comments`` webhook delivers these in near real time, but only when the
    subscription *and* the app's Webhooks config are both in place. An account
    missing either is otherwise deaf to comments forever, with no way to
    backfill — this poll is what makes that recoverable.
    """
    # Without an owner the own-comment filter below cannot recognise our own
    # activity, which would ingest every first comment we post as an inbound
    # customer message. Refuse to poll rather than do that.
    if not owner_id and not owner_handle:
        logger.warning("Skipping %s comment poll: no owner id or handle in credentials", platform)
        return []

    # ``since`` on the /media edge filters by MEDIA timestamp, not comment time
    # — the same trap as Facebook's /feed. It can only bound how far back we
    # look for *media*; passing the caller's ``since`` here would hide every new
    # comment on an older post. Comments are filtered on their own timestamp.
    media_floor = datetime.now(UTC) - timedelta(days=INSTAGRAM_MEDIA_WINDOW_DAYS)
    media_items = _fetch_media(request, platform, media_url, access_token, media_floor)

    # Normalize once here so the per-comment compare can never mix an aware
    # Graph timestamp with a naive caller-supplied ``since``.
    cutoff = None
    if since:
        cutoff = (since if since.tzinfo else since.replace(tzinfo=UTC)) - timedelta(
            hours=INSTAGRAM_COMMENT_LOOKBACK_HOURS
        )

    messages: list[InboxMessage] = []
    seen: set[str] = set()

    for media in media_items:
        # One unreadable or over-paginated media item must not discard the
        # comments already collected from every earlier item in this poll.
        try:
            comments = media.get("comments") or {}
            for comment in _iter_comments(request, host, access_token, comments):
                messages.extend(_comment_to_messages(comment, media, owner_id, owner_handle, cutoff, seen))
        except Exception as exc:
            logger.warning("Skipping %s comments for media %s: %s", platform, media.get("id"), exc)

    logger.debug("%s comment poll produced %d message(s)", platform, len(messages))
    return messages


def _fetch_media(request, platform: str, media_url: str, access_token: str, media_floor: datetime) -> list[dict]:
    """Read recent media with their comments expanded, degrading the field set.

    Only a 400 earns a shorter field set: an auth failure, a 5xx or a rate limit
    fails identically however few fields are asked for, so a second request is
    doomed and only costs quota.
    """
    last_error: Exception | None = None

    for fields in INSTAGRAM_COMMENT_FIELD_SETS:
        try:
            resp = request(
                "GET",
                media_url,
                access_token=access_token,
                params={
                    "fields": (f"id,timestamp,permalink,comments.limit({INSTAGRAM_COMMENTS_PER_MEDIA}){{{fields}}}"),
                    "limit": INSTAGRAM_MEDIA_SCAN_LIMIT,
                    "since": int(media_floor.timestamp()),
                },
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) != 400:
                raise
            last_error = exc
            logger.info("%s rejected the comment field set; retrying with fewer fields", platform)
            continue
        return resp.json().get("data", [])

    # The field-set tuple is never empty, so a fall-through means every set was
    # rejected with a 400 and last_error is set.
    raise last_error  # type: ignore[misc]


def _iter_comments(request, host: str, access_token: str, comments: dict):
    """Yield a media item's comments, following at most a bounded number of pages."""
    pages = 0
    while comments:
        yield from comments.get("data", [])

        next_url = (comments.get("paging") or {}).get("next")
        pages += 1
        if not next_url or pages >= INSTAGRAM_COMMENT_PAGE_LIMIT:
            if next_url:
                logger.debug("Instagram comment pagination capped at %d pages", INSTAGRAM_COMMENT_PAGE_LIMIT)
            return
        # Pin the cursor to the provider's own host — this is a URL from a
        # response body. And re-send the token: ``_request`` authenticates with
        # an Authorization header, so Graph builds ``paging.next`` from a query
        # string that never contained one.
        if urlparse(next_url).netloc != urlparse(host).netloc:
            logger.warning("Ignoring off-host Instagram comment paging URL")
            return
        comments = request("GET", next_url, access_token=access_token).json()


def _comment_to_messages(
    comment: dict,
    media: dict,
    owner_id: str,
    owner_handle: str,
    cutoff: datetime | None,
    seen: set[str],
) -> list[InboxMessage]:
    """Convert one comment and its replies to inbox messages."""
    messages = []
    top = _to_message(comment, media, owner_id, owner_handle, cutoff, seen, parent_id="")
    if top is not None:
        messages.append(top)

    # A skipped parent does not skip its replies: a customer answering our own
    # first comment is exactly the message we must not lose.
    for reply in (comment.get("replies") or {}).get("data", []):
        message = _to_message(
            reply,
            media,
            owner_id,
            owner_handle,
            cutoff,
            seen,
            parent_id=str(comment.get("id") or ""),
        )
        if message is not None:
            messages.append(message)
    return messages


def _to_message(
    comment: dict,
    media: dict,
    owner_id: str,
    owner_handle: str,
    cutoff: datetime | None,
    seen: set[str],
    *,
    parent_id: str,
) -> InboxMessage | None:
    """Convert one comment to an InboxMessage, or None to skip it."""
    comment_id = str(comment.get("id") or "")
    if not comment_id or comment_id in seen:
        return None

    author_id, author_handle = _comment_author(comment)
    if _is_own_comment(author_id, author_handle, owner_id, owner_handle):
        return None

    timestamp = parse_graph_time(comment.get("timestamp"))
    if timestamp is None:
        logger.debug("Skipping Instagram comment %s with unparseable timestamp", comment_id)
        return None
    if cutoff and timestamp < cutoff:
        return None

    seen.add(comment_id)
    media_id = str(media.get("id") or "")
    return InboxMessage(
        platform_message_id=comment_id,
        sender_id=author_id,
        sender_name=author_handle or "Instagram user",
        text=_comment_text(comment),
        timestamp=timestamp,
        message_type="comment",
        extra={
            "comment_id": comment_id,
            # Instagram media ids carry no page prefix to strip, so
            # PlatformPost.platform_post_id matches this value directly and the
            # two keys the inbox tries are the same id.
            "post_id": media_id,
            "stored_post_id": media_id,
            "parent_id": parent_id,
            "post_permalink_url": media.get("permalink", ""),
            # The platform user id, matching what the webhook path stores and
            # what FacebookProvider's poll emits. Re-polling a comment the
            # webhook already stored must not rewrite this column.
            "sender_handle": author_id or author_handle,
            "reply_edge": "comment",
            "source": "poll",
        },
    )
