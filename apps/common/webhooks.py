"""Inbound webhook from Resend: which addresses to stop mailing.

Resend accepts over SMTP and bounces asynchronously, so without this the app
cannot learn that an address is dead. The Resend log behind this change shows
repeated sends to addresses Resend itself had already marked ``suppressed`` —
wasted quota, and the kind of repeated hard bounce that costs a sending domain
its reputation.

Signature verification follows Resend's Svix scheme: the signed payload is
``{id}.{timestamp}.{body}``, and ``svix-signature`` carries one or more
space-separated ``v1,<base64 hmac>`` values (more than one during a secret
rotation), any of which may match.
"""

import base64
import hashlib
import hmac
import json
import logging
import time

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .models import EmailSuppression

logger = logging.getLogger(__name__)

# Reject anything older than this, so a captured request cannot be replayed to
# suppress an address long after the fact.
MAX_TIMESTAMP_SKEW_SECONDS = 5 * 60

SUPPRESSING_EVENTS = {
    "email.bounced": EmailSuppression.Reason.BOUNCED,
    "email.complained": EmailSuppression.Reason.COMPLAINED,
}


def _verify(request, secret: str) -> bool:
    """True when the request carries a valid, fresh Svix signature."""
    msg_id = request.headers.get("svix-id", "")
    timestamp = request.headers.get("svix-timestamp", "")
    signatures = request.headers.get("svix-signature", "")
    if not (msg_id and timestamp and signatures):
        return False

    try:
        if abs(time.time() - int(timestamp)) > MAX_TIMESTAMP_SKEW_SECONDS:
            logger.warning("Resend webhook: timestamp outside the accepted window")
            return False
    except (TypeError, ValueError):
        return False

    # Resend's secrets are published as "whsec_<base64>"; the bytes after the
    # prefix are the key.
    raw_secret = secret.split("_", 1)[1] if secret.startswith("whsec_") else secret
    try:
        key = base64.b64decode(raw_secret)
    except Exception:
        logger.error("Resend webhook: RESEND_WEBHOOK_SECRET is not valid base64")
        return False

    signed = f"{msg_id}.{timestamp}.".encode() + request.body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

    for candidate in signatures.split():
        version, _, value = candidate.partition(",")
        if version == "v1" and hmac.compare_digest(expected, value):
            return True
    return False


@csrf_exempt
@require_POST
@ratelimit(key="ip", rate="60/m", block=True)
def resend_webhook(request):
    """Record bounces and spam complaints as suppressions.

    Always answers 200 for a verified request, including for events we do not
    act on — a webhook that returns an error gets retried, and there is nothing
    to retry here.
    """
    secret = getattr(settings, "RESEND_WEBHOOK_SECRET", "")
    if not secret:
        # Refuse rather than accept unverified input: an unauthenticated caller
        # could otherwise suppress any address they liked.
        logger.error("Resend webhook called but RESEND_WEBHOOK_SECRET is not configured")
        return HttpResponseForbidden("Webhook secret not configured.")

    if not _verify(request, secret):
        logger.warning("Resend webhook: signature did not verify")
        return HttpResponseForbidden("Invalid signature.")

    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponse(status=400)

    event_type = payload.get("type", "")
    reason = SUPPRESSING_EVENTS.get(event_type)
    if reason is None:
        return HttpResponse(status=200)

    data = payload.get("data") or {}
    addresses = data.get("to") or []
    if isinstance(addresses, str):
        addresses = [addresses]

    for address in addresses:
        address = (address or "").strip().lower()
        if not address:
            continue
        _, created = EmailSuppression.objects.get_or_create(
            address=address,
            defaults={"reason": reason, "detail": str(data.get("reason", ""))[:500]},
        )
        if created:
            logger.warning("Suppressing %s after %s", address, event_type)

    return HttpResponse(status=200)
