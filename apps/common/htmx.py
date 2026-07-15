"""Small HTMX response helpers shared across apps."""

import json

from django.http import HttpResponse


def trigger_response(triggers, status=204):
    """Return an empty response that fires the given ``HX-Trigger`` events.

    ``triggers`` maps event name → detail, e.g.
    ``{"showToast": {...}, "approvalAction": True}``.
    """
    return HttpResponse(status=status, headers={"HX-Trigger": json.dumps(triggers)})


def toast_response(*, tone, title, body="", events=None):
    """204 that shows a client toast and optionally fires extra HX-Trigger events.

    The approval surfaces listen for ``showToast`` (renders the toast) plus a
    refresh event (e.g. ``approvalAction`` / ``portalAction``) to re-fetch their
    list. ``events`` is merged into the trigger payload.
    """
    triggers = {"showToast": {"tone": tone, "title": title, "body": body}}
    if events:
        triggers.update(events)
    return trigger_response(triggers)
