"""Shared Send API helpers for the Meta providers.

Facebook, Instagram (via Facebook Login) and Instagram (via Instagram Login)
all address a *person* rather than a message when replying, and all three build
the same request body. Keeping that in one place means a new payload shape only
has to be taught to the resolver once.
"""

from __future__ import annotations

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
