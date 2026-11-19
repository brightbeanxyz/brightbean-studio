"""Shared Send API helpers for the Meta providers.

Facebook, Instagram (via Facebook Login) and Instagram (via Instagram Login)
all address a *person* rather than a message when replying, and all three build
the same request body. Keeping that in one place means a new payload shape only
has to be taught to the resolver once.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from .exceptions import APIError, MessagingError, OAuthError, RateLimitError, TokenExpiredError
from .types import InboxMessage

logger = logging.getLogger(__name__)

META_DM_PLATFORMS = {"facebook", "instagram", "instagram_login"}


def enabled(value) -> bool:
    """Accept booleans and the strings stored by the credential admin."""
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def message_timestamp(value) -> datetime | None:
    """Parse Meta's millisecond webhook timestamp or timezone-aware API date."""
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            stamp = datetime.fromtimestamp(value / 1000, UTC)
        else:
            stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00").replace("+0000", "+00:00"))
        return stamp if stamp.tzinfo is not None and stamp.year >= 2000 else None
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def normalize_attachments(value) -> list[dict]:
    """Normalize webhook/API media without exposing raw payloads or unsafe URLs."""
    if isinstance(value, dict):
        value = value.get("data", [])
    if not isinstance(value, list):
        return []
    attachments = []
    for item in value:
        if not isinstance(item, dict):
            continue
        mime_type = item.get("mime_type")
        mime_type = mime_type if isinstance(mime_type, str) else ""
        kind = str(item.get("type") or mime_type.split("/")[0] or "file")
        payload = item.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        url = item.get("url") or payload.get("url")
        for key in ("image_data", "video_data", "audio_data", "file_data"):
            if isinstance(item.get(key), dict):
                kind = key.removesuffix("_data")
                url = url or item[key].get("url") or item[key].get("preview_url")
        try:
            parsed = urlsplit(str(url or ""))
            safe = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
        except ValueError:
            safe = False
        attachments.append({"type": kind, "url": str(url) if safe else ""})
    return attachments


def dm_extra(message: dict, *, sender_id: str, conversation_id: str = "") -> dict:
    stamp = message_timestamp(message.get("created_time"))
    return {
        "sender_id": sender_id,
        "conversation_id": conversation_id,
        "platform_timestamp": stamp.isoformat() if stamp else None,
        "attachments": normalize_attachments(message.get("attachments", [])),
        "is_deleted": bool(message.get("is_deleted")),
        "is_unsupported": bool(message.get("is_unsupported")),
    }


def validate_instagram_text(text: str, *, platform: str) -> None:
    if not text.strip() or len(text.encode("utf-8")) > 1000:
        raise MessagingError(
            "Instagram DM replies must contain text and fit within 1,000 UTF-8 bytes.", platform=platform
        )


def require_message_id(data: dict, *, platform: str) -> str:
    message_id = data.get("message_id")
    if not isinstance(message_id, str) or not message_id:
        raise MessagingError(
            "Delivery could not be confirmed. Check the conversation before retrying.", platform=platform
        )
    return message_id


class InstagramMessageBatch(list[InboxMessage]):
    """Messages and the continuation to commit after importing them.

    None means the DM channel did not complete a poll; an empty dict means the
    walk finished and the previous continuation can be cleared.
    """

    def __init__(self, messages=(), *, poll_state: dict | None = None):
        super().__init__(messages)
        self.poll_state = poll_state


def meta_subscription_needs_reconnect(exc: Exception) -> bool:
    """Recognize auth/permission failures without treating every 400 as auth."""
    if isinstance(exc, TokenExpiredError | OAuthError):
        return True
    if isinstance(exc, RateLimitError) or not isinstance(exc, APIError):
        return False
    if exc.status_code in {401, 403}:
        return True
    raw = exc.raw_response
    error = raw.get("error") if isinstance(raw, dict) else None
    if isinstance(error, dict):
        # Meta uses 400 for revoked tokens (190) and missing permissions (10/200).
        code = error.get("code")
        return isinstance(code, int) and code in {10, 190, 200}
    return isinstance(error, str) and error in {"invalid_token", "invalid_grant", "ExpiredToken", "InvalidToken"}


# Graph answers a conversation page in 2-4 s and the conversation list in up to
# ~9 s, so a request needs its full timeout. Shrinking it as the walk budget runs
# out made the last call of every poll time out, which threw the whole poll away.
DM_WALK_BUDGET_SECONDS = 20
DM_REQUEST_TIMEOUT_SECONDS = 10


def fetch_instagram_page_messages(
    request, *, base_url, page_id, owner_id, access_token, since=None, poll_state=None
) -> InstagramMessageBatch:
    """Walk conversations and messages with durable continuation and bounds.

    Keep at most one conversation page's remaining IDs and the current message
    cursor. A later worker resumes that exact walk instead of spending every
    poll's budget on the same early history. Rebuild URLs locally, never follow
    platform-provided URLs, and ignore the shared comment/DM high-water mark.
    """
    started = time.monotonic()
    remaining_calls = 100
    completed_calls = 0
    messages = []
    state = poll_state if isinstance(poll_state, dict) else {}
    if state.get("page_id") != str(page_id) or state.get("owner_id") != str(owner_id):
        state = {}
    conversations = list(state.get("conversations") or [])
    conversation_after = state.get("conversation_after")
    message_after = state.get("message_after")
    listed_conversations = bool(conversations or conversation_after)
    seen_conversation_cursors = {conversation_after} if conversation_after else set()
    seen_message_cursors = {message_after} if message_after else set()

    def page(url, params, after):
        nonlocal remaining_calls
        query = {**params, "limit": 100}
        if after:
            query["after"] = after
        remaining_calls -= 1
        return request(
            "GET",
            url,
            access_token=access_token,
            params=query,
            timeout=DM_REQUEST_TIMEOUT_SECONDS,
        ).json()

    def next_cursor(data, seen):
        paging = data.get("paging") or {}
        after = (paging.get("cursors") or {}).get("after")
        if not paging.get("next") or not after or after in seen:
            return None
        seen.add(after)
        return after

    while remaining_calls and time.monotonic() - started < DM_WALK_BUDGET_SECONDS:
        if not conversations:
            if listed_conversations and not conversation_after:
                break
            try:
                data = page(
                    f"{base_url}/{page_id}/conversations",
                    {"platform": "instagram", "fields": "id"},
                    conversation_after,
                )
            except httpx.TimeoutException:
                if not completed_calls:
                    raise
                logger.warning("Instagram DM poll timed out; keeping progress for the next poll")
                break
            completed_calls += 1
            conversations = [str(convo["id"]) for convo in data.get("data", []) if convo.get("id")]
            conversation_after = next_cursor(data, seen_conversation_cursors)
            listed_conversations = True
            continue
        convo_id = conversations[0]
        try:
            data = page(
                f"{base_url}/{convo_id}/messages",
                {"fields": "id,message,from,created_time,attachments"},
                message_after,
            )
        except httpx.TimeoutException:
            # Keep the messages and cursor gathered so far. Raising here would
            # discard them and restart the same walk on the next poll.
            if not completed_calls:
                raise
            logger.warning("Instagram DM poll timed out; keeping progress for the next poll")
            break
        completed_calls += 1
        for msg in data.get("data", []):
            sender = msg.get("from") or {}
            sender_id = str(sender.get("id") or "")
            stamp = message_timestamp(msg.get("created_time"))
            if not sender_id or sender_id in {str(owner_id), str(page_id)} or msg.get("is_echo"):
                continue
            # The sync engine's high-water mark includes comments. A newer
            # comment must never hide an older DM after a failed DM poll.
            if not msg.get("id") or stamp is None:
                continue
            messages.append(
                InboxMessage(
                    platform_message_id=str(msg["id"]),
                    sender_id=sender_id,
                    sender_name=sender.get("name") or sender.get("username") or sender_id,
                    text=msg.get("message") or "",
                    timestamp=stamp,
                    message_type="dm",
                    extra=dm_extra(msg, sender_id=sender_id, conversation_id=str(convo_id)),
                )
            )
        message_after = next_cursor(data, seen_message_cursors)
        if not message_after:
            conversations.pop(0)
            seen_message_cursors.clear()
    continuation = {}
    if conversations or conversation_after or not listed_conversations:
        logger.warning("Instagram DM poll reached its bounded request/time budget")
        continuation = {
            "page_id": str(page_id),
            "owner_id": str(owner_id),
            "conversations": conversations,
            "conversation_after": conversation_after,
            "message_after": message_after,
        }
    return InstagramMessageBatch(messages, poll_state=continuation)


def merge_page_message_subscription(
    request, *, base_url, page_id, access_token, app_id, required_fields=("messages",)
) -> bool:
    """Add messages while preserving this app's existing Page fields."""
    if not app_id:
        raise MessagingError("Configure the Meta App ID before enabling DM notifications.")
    url = f"{base_url}/{page_id}/subscribed_apps"
    data = request("GET", url, access_token=access_token).json()
    fields = set(required_fields)
    for app in data.get("data", []):
        if str(app.get("id")) == str(app_id):
            fields.update(app.get("subscribed_fields") or [])
    resp = request("POST", url, access_token=access_token, params={"subscribed_fields": ",".join(sorted(fields))})
    if not resp.json().get("success"):
        return False
    readback = request("GET", url, access_token=access_token).json()
    return any(
        str(app.get("id")) == str(app_id) and fields.issubset(app.get("subscribed_fields") or [])
        for app in readback.get("data", [])
    )


# Where the person's platform-scoped ID hides, in priority order. The inbox view
# passes ``recipient_id`` explicitly, so it wins; a webhook messaging event
# nests it under ``sender``; a polled conversation carries ``from``; and
# ``sender_id`` is what the provider stores when polling.
_RECIPIENT_KEYS = ("recipient_id", "sender", "from", "sender_id")


def resolve_recipient_id(extra: dict | None) -> str:
    """Return the scoped ID (PSID or IGSID) of the person being replied to.

    Returns an empty string when the payload carries no sender, which callers
    treat as "cannot send" rather than guessing a recipient.
    """
    extra = extra or {}
    for key in _RECIPIENT_KEYS:
        value = extra.get(key)
        if isinstance(value, dict):
            value = value.get("id")
        if value:
            return str(value)
    return ""


def build_send_payload(recipient_id: str, text: str, *, human_agent: bool = False) -> dict:
    """Build a Send API request body.

    Past 24 hours Meta only accepts a tagged message, and HUMAN_AGENT is the tag
    for a person (never a bot) answering within 7 days.
    """
    payload: dict = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "messaging_type": "MESSAGE_TAG" if human_agent else "RESPONSE",
    }
    if human_agent:
        payload["tag"] = "HUMAN_AGENT"
    return payload
