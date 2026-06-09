"""Inbound webhook receivers for Facebook/Instagram and YouTube."""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from apps.common.validators import safe_xml_fromstring
from apps.credentials.models import resolve_app_secret, resolve_app_secrets
from apps.social_accounts.models import SocialAccount

from .models import InboxMessage
from .sentiment import analyze_sentiment

logger = logging.getLogger(__name__)


# --- Meta (Facebook + Instagram) shared helpers ---


def _meta_verify(request, configured_token: str):
    """Handle Meta webhook verification handshake.

    Meta hits this endpoint with hub.mode=subscribe + hub.verify_token + hub.challenge.
    We compare the supplied token to the one configured for this endpoint and echo
    the challenge on match.
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge", "")

    if not configured_token:
        logger.error("Webhook verify token not configured. Rejecting verification.")
        return HttpResponseForbidden("Webhook verify token not configured.")

    if mode == "subscribe" and token == configured_token:
        return HttpResponse(challenge, content_type="text/plain")
    return HttpResponseForbidden("Verification failed.")


def _verify_meta_signature(body: bytes, signature_header: str, app_secret: str) -> bool:
    """Verify HMAC-SHA256 signature (X-Hub-Signature-256) from Meta."""
    if not app_secret:
        logger.error("Meta app_secret not configured. Cannot verify webhook.")
        return False

    expected = (
        "sha256="
        + hmac.new(
            app_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature_header)


def _meta_receive(request, platforms: list[str]):
    """Validate the HMAC signature and dispatch incoming Meta webhook events.

    A delivery is signed by exactly one Meta app. We accept the request only if
    the signature matches a configured app secret, then process events *only* for
    accounts whose owning org's secret actually signed the body (see
    ``_process_meta_events``) — so one org's secret can never authorize writes
    into another org's accounts.
    """
    signature = request.headers.get("X-Hub-Signature-256", "")
    candidate_secrets = resolve_app_secrets(*platforms)
    valid_secrets = {secret for secret in candidate_secrets if _verify_meta_signature(request.body, signature, secret)}
    if not valid_secrets:
        logger.warning("Meta webhook: signature did not match any configured app secret.")
        return HttpResponseForbidden("Invalid signature.")

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in Meta webhook payload.")
        return HttpResponse("Bad request", status=400)

    _process_meta_events(payload, platforms, valid_secrets)
    return HttpResponse("OK", status=200)


def _process_meta_events(payload: dict, platforms: list[str], valid_secrets: set[str]):
    """Process Meta (Facebook/Instagram) webhook events into InboxMessages.

    An event is processed only for SocialAccounts whose platform is in
    `platforms` AND whose owning org's app secret signed this delivery (i.e. is in
    `valid_secrets`). This binds each event to the org that owns the signing app,
    preventing one org's secret from forging events into another org's accounts.
    """
    for entry in payload.get("entry", []):
        page_id = entry.get("id")
        if not page_id:
            continue

        accounts = SocialAccount.objects.filter(
            account_platform_id=page_id,
            platform__in=platforms,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        ).select_related("workspace__organization")

        for account in accounts:
            account_secret = resolve_app_secret(account.platform, account.workspace.organization_id)
            if not account_secret or account_secret not in valid_secrets:
                logger.warning(
                    "Meta webhook: signature not valid for account %s's org app; skipping event.",
                    account.id,
                )
                continue

            for change in entry.get("changes", []):
                _handle_facebook_change(account, change)

            for messaging in entry.get("messaging", []):
                _handle_facebook_messaging(account, messaging)


# --- Webhook entry points ---


@csrf_exempt
@ratelimit(key="ip", rate="60/m", block=True)
@require_http_methods(["GET", "POST"])
def facebook_webhook(request):
    """Facebook & Instagram (Facebook Login) webhook endpoint.

    GET:  Verification handshake (hub.mode, hub.verify_token, hub.challenge).
    POST: Incoming events with HMAC-SHA256 signature in X-Hub-Signature-256.
    """
    if request.method == "GET":
        return _meta_verify(request, settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN)
    # Facebook + Instagram (Facebook Login) share one Meta app.
    return _meta_receive(request, platforms=["facebook", "instagram"])


@csrf_exempt
@ratelimit(key="ip", rate="60/m", block=True)
@require_http_methods(["GET", "POST"])
def instagram_login_webhook(request):
    """Instagram (Direct, via Instagram Login) webhook endpoint.

    Separate from `facebook_webhook` because it uses its own verify token and
    its own app secret (the Instagram App is distinct from the parent Meta App
    when authenticating via Instagram Login).
    """
    if request.method == "GET":
        return _meta_verify(request, settings.INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN)
    return _meta_receive(request, platforms=["instagram_login"])


# --- Event handlers (shared between facebook + instagram_login) ---


def _handle_facebook_change(account, change: dict):
    """Handle a single Facebook change event (comment, mention, etc.)."""
    field = change.get("field", "")
    value = change.get("value", {})

    if field == "feed":
        _upsert_facebook_comment(account, value)
    elif field == "mention":
        _upsert_facebook_mention(account, value)


def _upsert_facebook_comment(account, value: dict):
    """Upsert a Facebook comment from a webhook event."""
    comment_id = value.get("comment_id") or value.get("id")
    if not comment_id:
        return

    from_data = value.get("from", {})
    text = value.get("message", "")

    _create_if_new(
        account=account,
        platform_message_id=str(comment_id),
        message_type=InboxMessage.MessageType.COMMENT,
        sender_name=from_data.get("name", "Unknown"),
        sender_id=from_data.get("id", ""),
        body=text,
        extra=value,
    )


def _upsert_facebook_mention(account, value: dict):
    """Upsert a Facebook mention from a webhook event."""
    mention_id = value.get("post_id") or value.get("id")
    if not mention_id:
        return

    from_data = value.get("from", {})
    text = value.get("message", "")

    _create_if_new(
        account=account,
        platform_message_id=str(mention_id),
        message_type=InboxMessage.MessageType.MENTION,
        sender_name=from_data.get("name", "Unknown"),
        sender_id=from_data.get("id", ""),
        body=text,
        extra=value,
    )


def _handle_facebook_messaging(account, messaging: dict):
    """Handle a Facebook/Instagram messaging event (DM)."""
    message_data = messaging.get("message", {})
    mid = message_data.get("mid")
    if not mid:
        return

    sender = messaging.get("sender", {})
    text = message_data.get("text", "")

    _create_if_new(
        account=account,
        platform_message_id=str(mid),
        message_type=InboxMessage.MessageType.DM,
        sender_name=sender.get("name", sender.get("id", "Unknown")),
        sender_id=sender.get("id", ""),
        body=text,
        extra=messaging,
    )


def _create_if_new(
    account,
    platform_message_id: str,
    message_type: str,
    sender_name: str,
    sender_id: str,
    body: str,
    extra: dict,
):
    """Create InboxMessage if it doesn't already exist (deduplication)."""
    from django.utils import timezone

    obj, created = InboxMessage.objects.get_or_create(
        social_account=account,
        platform_message_id=platform_message_id,
        defaults={
            "workspace": account.workspace,
            "message_type": message_type,
            "sender_name": sender_name,
            "sender_handle": sender_id,  # Platform user ID as fallback handle
            "body": body,
            "sentiment": analyze_sentiment(body),
            "extra": extra,
            "received_at": timezone.now(),
        },
    )
    if created:
        from .tasks import InboxSyncEngine

        InboxSyncEngine()._notify_new_message(obj)


# --- YouTube PubSubHubbub ---


@csrf_exempt
@ratelimit(key="ip", rate="60/m", block=True)
@require_http_methods(["GET", "POST"])
def youtube_webhook(request):
    """YouTube PubSubHubbub webhook endpoint.

    GET:  Subscription verification (echo hub.challenge).
    POST: Atom XML notification for new comments/activity.
    """
    if request.method == "GET":
        challenge = request.GET.get("hub.challenge", "")
        return HttpResponse(challenge, content_type="text/plain")

    # Verify HMAC - reject if secret is not configured
    webhook_secret = settings.YOUTUBE_WEBHOOK_SECRET
    if not webhook_secret:
        logger.error("YOUTUBE_WEBHOOK_SECRET is not configured. Rejecting webhook POST.")
        return HttpResponseForbidden("Webhook secret not configured.")

    signature = request.headers.get("X-Hub-Signature", "")
    expected = (
        "sha1="
        + hmac.new(
            webhook_secret.encode(),
            request.body,
            hashlib.sha1,
        ).hexdigest()
    )
    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid YouTube webhook signature.")
        return HttpResponseForbidden("Invalid signature.")

    try:
        _process_youtube_notification(request.body)
    except Exception:
        logger.exception("Error processing YouTube webhook.")

    return HttpResponse("OK", status=200)


def _process_youtube_notification(body: bytes):
    """Parse Atom XML notification from YouTube and upsert messages."""
    root = safe_xml_fromstring(body)
    if root is None:
        logger.warning("Invalid or unsafe XML in YouTube webhook payload.")
        return

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }

    for entry in root.findall("atom:entry", ns):
        video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
        channel_id = entry.findtext("yt:channelId", default="", namespaces=ns)
        title = entry.findtext("atom:title", default="", namespaces=ns)
        entry_id = entry.findtext("atom:id", default="", namespaces=ns)

        if not channel_id or not entry_id:
            continue

        accounts = SocialAccount.objects.filter(
            account_platform_id=channel_id,
            platform="youtube",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        ).select_related("workspace__organization")

        for account in accounts:
            _create_if_new(
                account=account,
                platform_message_id=entry_id,
                message_type=InboxMessage.MessageType.COMMENT,
                sender_name="YouTube",
                sender_id=channel_id,
                body=title,
                extra={"video_id": video_id, "entry_id": entry_id},
            )
