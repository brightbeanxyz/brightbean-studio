"""One-click unsubscribe for notification email.

Until now the only way out of a notification was a footer link to
``/notifications/preferences/`` — a page that requires signing in. Someone
buried by mail they did not ask for will not sign in to stop it; they will press
the spam button, which costs the sending domain far more than the unsubscribe
would have. Gmail and Yahoo now also expect bulk senders to honour RFC 8058
one-click unsubscribe.

The token is a signed ``(user_id, event_type)`` pair. It proves the request came
from an email we sent, without a session, and it can only ever turn that email
off for one person — the worst a leaked token allows is exactly what the
recipient was being offered anyway.

A daily digest covers every event type at once, so its link cannot name one.
Those carry ALL_EVENTS instead, which turns off notification email across the
board — the only reading of "unsubscribe" on an email that collects all of it.
"""

import logging

from django.conf import settings
from django.core import signing
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Channel, EventType, NotificationPreference

logger = logging.getLogger(__name__)

SALT = "notifications.unsubscribe"
# Generous, because an email can sit unread for a long time and a dead
# unsubscribe link is worse than no link at all.
MAX_TOKEN_AGE_SECONDS = 365 * 24 * 60 * 60

# Stands in for "every event type" in a token, for the daily digest. Deliberately
# not a valid EventType value, so it can never collide with one.
ALL_EVENTS = "__all__"
ALL_EVENTS_LABEL = "Notification"


def make_token(user_id, event_type: str) -> str:
    return signing.dumps({"u": str(user_id), "e": str(event_type)}, salt=SALT)


def unsubscribe_url(user_id, event_type: str) -> str:
    app_url = getattr(settings, "APP_URL", "http://localhost:8000").rstrip("/")
    path = reverse("notifications:unsubscribe", kwargs={"token": make_token(user_id, event_type)})
    return f"{app_url}{path}"


def list_unsubscribe_headers(user_id, event_type: str | None) -> dict[str, str]:
    """RFC 2369 + RFC 8058 headers for a notification-class email.

    ``event_type=None`` is the daily digest, which spans every type.
    """
    url = unsubscribe_url(user_id, event_type if event_type is not None else ALL_EVENTS)
    return {
        "List-Unsubscribe": f"<{url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def _decode(token: str) -> tuple[str, str] | None:
    """(user_id, event_type) from a token, or None if it is not one of ours."""
    try:
        payload = signing.loads(token, salt=SALT, max_age=MAX_TOKEN_AGE_SECONDS)
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict):
        return None

    user_id = payload.get("u")
    event_type = payload.get("e")
    # Both are read defensively rather than subscripted: this endpoint is
    # public and unauthenticated, so a token of an unexpected shape has to come
    # back as a 400, not a 500.
    if not user_id or (event_type not in EventType.values and event_type != ALL_EVENTS):
        return None
    return str(user_id), str(event_type)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def unsubscribe(request, token):
    """Turn off email for one event type.

    Only POST changes anything. That is not ceremony: mail scanners and link
    prefetchers — Outlook Safe Links, corporate gateways, antivirus proxies —
    routinely fetch every URL they find in a message, including the one in the
    List-Unsubscribe header. If a GET unsubscribed, those fetches would silently
    switch off someone's publish-failure alerts without them ever clicking,
    which is the same silent-alerting failure this whole area exists to prevent.
    RFC 8058 one-click posts, so conformant clients are unaffected; a person
    following the link gets a page with a single button.

    CSRF is exempt because the signed token *is* the authorization, and a mail
    client performing a one-click POST has no session to take a token from. The
    worst a leaked token allows is exactly what its holder was already being
    offered: turning off one event type's email for one person.
    """
    decoded = _decode(token)
    if decoded is None:
        return HttpResponse("This unsubscribe link is not valid.", status=400, content_type="text/plain")

    user_id, event_type = decoded
    label = ALL_EVENTS_LABEL if event_type == ALL_EVENTS else EventType(event_type).label
    # ALL_EVENTS is the daily digest: it collects every type, so the only
    # honest thing "unsubscribe" can do is switch all of them off.
    event_types = list(EventType.values) if event_type == ALL_EVENTS else [event_type]

    if request.method == "GET":
        return render(request, "notifications/unsubscribe.html", {"label": label, "token": token})

    try:
        for value in event_types:
            NotificationPreference.objects.update_or_create(
                user_id=user_id,
                event_type=value,
                channel=Channel.EMAIL,
                defaults={"is_enabled": False},
            )
    except IntegrityError:
        # The account is gone. Nothing to switch off, and nothing the person
        # reading this can do about it either.
        logger.info("Unsubscribe for unknown user %s (%s)", user_id, event_type)
        return HttpResponse("This unsubscribe link is not valid.", status=400, content_type="text/plain")

    logger.info("Unsubscribed user %s from %s email (%d event type(s))", user_id, event_type, len(event_types))
    return render(request, "notifications/unsubscribed.html", {"label": label})
