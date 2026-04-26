"""Client onboarding views.

Management views (authenticated): create/revoke/send connection links, dismiss checklist.
Public views (no auth): connection link page, OAuth flow, done notification.
"""

import logging
import secrets
from datetime import timedelta

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.credentials.models import PlatformCredential
from apps.members.decorators import require_permission
from apps.members.models import WorkspaceMembership
from apps.notifications.engine import notify
from apps.notifications.models import EventType
from apps.social_accounts.views import (
    _create_or_update_account,
    _get_configured_platforms,
    _get_provider_for_platform,
    _normalize_mastodon_instance_url,
    _resolve_mastodon_extra_creds,
)

from .models import ConnectionLink, ConnectionLinkUsage, OnboardingChecklist

logger = logging.getLogger(__name__)

CONNECTION_LINK_OAUTH_SESSION_KEY = "connection_link_oauth"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes
MAX_OAUTH_INITIATIONS_PER_HOUR = 20


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _get_connection_link_or_none(token):
    """Look up a ConnectionLink by token, return None if not found."""
    try:
        return ConnectionLink.objects.select_related("workspace__organization").get(token=token)
    except ConnectionLink.DoesNotExist:
        return None


def _sign_connection_link_state(workspace_id, platform, token, nonce):
    """Create a signed OAuth state for the connection link flow."""
    return signing.dumps(
        {
            "workspace_id": str(workspace_id),
            "platform": platform,
            "connection_link_token": token,
            "nonce": nonce,
            "flow": "connection_link",
        },
        salt="social-oauth-state",
    )


def _unsign_connection_link_state(state_str):
    """Verify and decode the connection link OAuth state."""
    return signing.loads(
        state_str,
        salt="social-oauth-state",
        max_age=OAUTH_STATE_MAX_AGE,
    )


def _build_connection_redirect_uri(request, platform):
    """Build the OAuth callback URL for connection link flow."""
    return request.build_absolute_uri(reverse("onboarding:oauth_callback", kwargs={"platform": platform}))


def _check_rate_limit(token):
    """Rate limit OAuth initiations per token. Returns True if allowed."""
    key = f"connection_link_oauth_rate:{token}"
    count = cache.get(key, 0)
    if count >= MAX_OAUTH_INITIATIONS_PER_HOUR:
        return False
    cache.set(key, count + 1, timeout=3600)
    return True


# ------------------------------------------------------------------
# Management Views (authenticated)
# ------------------------------------------------------------------


@login_required
@require_permission("manage_social_accounts")
@require_POST
def create_link(request, workspace_id):
    """Create a new connection link for a workspace."""
    expiry_days = int(request.POST.get("expiry_days", 7))
    expiry_days = max(1, min(expiry_days, 90))  # clamp 1-90 days

    link = ConnectionLink.objects.create(
        workspace_id=workspace_id,
        created_by=request.user,
        expires_at=timezone.now() + timedelta(days=expiry_days),
    )

    link_url = request.build_absolute_uri(reverse("onboarding:connection_page", kwargs={"token": link.token}))

    if request.headers.get("HX-Request"):
        return render(
            request,
            "onboarding/partials/_connection_link_created.html",
            {"link": link, "link_url": link_url},
        )

    messages.success(request, "Connection link created.")
    return redirect("social_accounts:list", workspace_id=workspace_id)


@login_required
@require_permission("manage_social_accounts")
@require_POST
def revoke_link(request, workspace_id, link_id):
    """Revoke an active connection link."""
    link = get_object_or_404(ConnectionLink.objects.for_workspace(workspace_id), id=link_id)
    link.revoked_at = timezone.now()
    link.save(update_fields=["revoked_at"])

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200)

    messages.success(request, "Connection link revoked.")
    return redirect("social_accounts:list", workspace_id=workspace_id)


@login_required
@require_permission("manage_social_accounts")
@require_POST
def send_link_email(request, workspace_id, link_id):
    """Send the connection link to a client email."""
    link = get_object_or_404(ConnectionLink.objects.for_workspace(workspace_id), id=link_id)
    email = request.POST.get("email", "").strip()

    if not email:
        messages.error(request, "Email address is required.")
        return redirect("social_accounts:list", workspace_id=workspace_id)

    if not link.is_active:
        messages.error(request, "This connection link is no longer active.")
        return redirect("social_accounts:list", workspace_id=workspace_id)

    link_url = request.build_absolute_uri(reverse("onboarding:connection_page", kwargs={"token": link.token}))
    org = link.workspace.organization

    context = {
        "link_url": link_url,
        "org_name": org.name,
        "workspace_name": link.workspace.name,
        "expires_at": link.expires_at,
    }

    text_content = render_to_string("onboarding/email/connection_link.txt", context)
    html_content = render_to_string("onboarding/email/connection_link.html", context)

    msg = EmailMultiAlternatives(
        subject=f"{org.name} - Connect your social accounts",
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
        to=[email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)

    messages.success(request, f"Connection link sent to {email}.")
    return redirect("social_accounts:list", workspace_id=workspace_id)


@login_required
@require_GET
def checklist_partial(request, workspace_id):
    """Return the checklist partial for htmx polling."""
    from apps.onboarding.context_processors import onboarding_checklist

    ctx = onboarding_checklist(request)
    return render(request, "onboarding/partials/_checklist.html", ctx)


@login_required
@require_POST
def dismiss_checklist(request, workspace_id):
    """Dismiss the onboarding checklist for the current user + workspace."""
    OnboardingChecklist.objects.update_or_create(
        user=request.user,
        workspace_id=workspace_id,
        defaults={
            "is_dismissed": True,
            "dismissed_at": timezone.now(),
        },
    )

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200)

    return redirect("calendar:calendar", workspace_id=workspace_id)


# ------------------------------------------------------------------
# Public Connection Link Views (NO auth required)
# ------------------------------------------------------------------


@require_GET
def connection_page(request, token):
    """Render the public connection link page."""

    link = _get_connection_link_or_none(token)
    if not link:
        return render(request, "onboarding/connection_expired.html", status=404)

    if not link.is_active:
        return render(
            request,
            "onboarding/connection_expired.html",
            {
                "org_name": link.workspace.organization.name,
                "is_revoked": link.is_revoked,
            },
        )

    workspace = link.workspace
    org = workspace.organization

    # Get configured platforms
    configured_platforms = _get_configured_platforms(org.id)

    # Get accounts already connected via this link
    connected_usages = ConnectionLinkUsage.objects.filter(connection_link=link).select_related("social_account")
    connected_accounts = {usage.social_account.platform: usage.social_account for usage in connected_usages}

    # Store token in session for OAuth flow
    request.session["connection_link_token"] = token

    # Pop session error (display once)
    session_error = request.session.pop("connection_link_error", None)

    return render(
        request,
        "onboarding/connection_page.html",
        {
            "link": link,
            "workspace": workspace,
            "error": session_error,
            "org": org,
            "platform_choices": PlatformCredential.Platform.choices,
            "configured_platforms": configured_platforms,
            "connected_accounts": connected_accounts,
        },
    )


@csp_update(
    FORM_ACTION="'self' https://accounts.google.com https://www.facebook.com https://api.instagram.com https://www.instagram.com https://threads.net https://www.linkedin.com https://www.pinterest.com https://www.tiktok.com"
)
@require_POST
def connection_oauth_start(request, token):
    """Initiate OAuth flow from the connection link page."""
    link = _get_connection_link_or_none(token)
    if not link or not link.is_active:
        return render(request, "onboarding/connection_expired.html", status=400)

    # Rate limit
    if not _check_rate_limit(token):
        request.session["connection_link_error"] = "Too many connection attempts. Please try again later."
        return redirect("onboarding:connection_page", token=token)

    platform = request.POST.get("platform", "").strip()
    if platform not in dict(PlatformCredential.Platform.choices):
        return redirect("onboarding:connection_page", token=token)

    org = link.workspace.organization
    configured_platforms = _get_configured_platforms(org.id)
    if platform not in configured_platforms:
        return redirect("onboarding:connection_page", token=token)

    # Bluesky and Mastodon use their own forms on the connection page
    # (not standard OAuth via this endpoint), so reject them here.
    if platform in (
        PlatformCredential.Platform.BLUESKY,
        PlatformCredential.Platform.MASTODON,
    ):
        return redirect("onboarding:connection_page", token=token)

    # Standard OAuth flow
    provider = _get_provider_for_platform(platform, org.id)
    nonce = secrets.token_urlsafe(32)
    state = _sign_connection_link_state(link.workspace_id, platform, token, nonce)

    # Store in session
    request.session[CONNECTION_LINK_OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(link.workspace_id),
        "platform": platform,
        "token": token,
    }

    redirect_uri = _build_connection_redirect_uri(request, platform)
    auth_url = provider.get_auth_url(redirect_uri, state)
    return redirect(auth_url)


@require_GET
def connection_oauth_callback(request, platform):
    """Handle OAuth callback for connection link flow."""
    error = request.GET.get("error")
    if error:
        error_desc = request.GET.get("error_description", error)
        session_data = request.session.pop(CONNECTION_LINK_OAUTH_SESSION_KEY, {})
        token = session_data.get("token")
        if token:
            request.session["connection_link_error"] = f"Authorization failed: {error_desc}"
            return redirect("onboarding:connection_page", token=token)
        return render(
            request,
            "onboarding/connection_expired.html",
            {"error": error_desc},
        )

    code = request.GET.get("code")
    state_str = request.GET.get("state")

    if not code or not state_str:
        return render(
            request,
            "onboarding/connection_expired.html",
            {"error": "Missing authorization code or state parameter."},
        )

    # Validate state
    try:
        state_data = _unsign_connection_link_state(state_str)
    except signing.BadSignature:
        return render(
            request,
            "onboarding/connection_expired.html",
            {"error": "Invalid or expired OAuth state. Please try again."},
        )

    # Verify this is a connection link flow
    if state_data.get("flow") != "connection_link":
        return render(
            request,
            "onboarding/connection_expired.html",
            {"error": "Invalid OAuth flow."},
        )

    # Validate nonce from session
    session_data = request.session.pop(CONNECTION_LINK_OAUTH_SESSION_KEY, {})
    if not session_data or session_data.get("nonce") != state_data.get("nonce"):
        return render(
            request,
            "onboarding/connection_expired.html",
            {"error": "OAuth session mismatch. Please try again."},
        )

    # Validate platform matches
    if state_data.get("platform") != platform:
        return render(
            request,
            "onboarding/connection_expired.html",
            {"error": "Platform mismatch in OAuth callback."},
        )

    # Look up connection link
    token = state_data.get("connection_link_token")
    link = _get_connection_link_or_none(token)
    if not link or not link.is_active:
        return render(request, "onboarding/connection_expired.html")

    workspace_id = str(link.workspace_id)
    org = link.workspace.organization

    try:
        extra_creds: dict = {}
        if platform == PlatformCredential.Platform.MASTODON:
            extra_creds = _resolve_mastodon_extra_creds(session_data)

        provider = _get_provider_for_platform(platform, org.id, **extra_creds)
        redirect_uri = _build_connection_redirect_uri(request, platform)
        tokens = provider.exchange_code(code, redirect_uri)
        profile = provider.get_profile(tokens.access_token)

        # Handle Facebook/Instagram multi-page: auto-connect first page
        if platform in (
            PlatformCredential.Platform.FACEBOOK,
            PlatformCredential.Platform.INSTAGRAM,
        ) and hasattr(provider, "get_user_pages"):
            pages = provider.get_user_pages(tokens.access_token)
            if pages:
                from providers.types import AccountProfile

                for page in pages:
                    page_profile = AccountProfile(
                        platform_id=page["id"],
                        name=page["name"],
                        handle=page.get("handle"),
                        avatar_url=page.get("picture", ""),
                        follower_count=page.get("followers_count", 0),
                    )
                    account = _create_or_update_account(
                        workspace_id=workspace_id,
                        platform=platform,
                        profile=page_profile,
                        access_token=page.get("access_token", tokens.access_token),
                        refresh_token=tokens.refresh_token,
                        expires_in=tokens.expires_in,
                    )
                    ConnectionLinkUsage.objects.get_or_create(
                        connection_link=link,
                        social_account=account,
                    )
                return redirect("onboarding:connection_page", token=token)

        # Standard single-account flow
        account = _create_or_update_account(
            workspace_id=workspace_id,
            platform=platform,
            profile=profile,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            instance_url=extra_creds.get("instance_url", ""),
        )
        ConnectionLinkUsage.objects.get_or_create(
            connection_link=link,
            social_account=account,
        )

    except Exception:
        logger.exception("Connection link OAuth callback failed for %s", platform)
        # Store error in session to display on connection page
        request.session["connection_link_error"] = "Failed to connect account. Please try again."

    return redirect("onboarding:connection_page", token=token)


@require_POST
def connection_done(request, token):
    """Client clicks 'Done' - notify workspace managers."""
    link = _get_connection_link_or_none(token)
    if not link:
        return render(request, "onboarding/connection_expired.html", status=404)

    # Count connected accounts via this link
    connected_count = ConnectionLinkUsage.objects.filter(connection_link=link).count()
    connected_accounts = (
        ConnectionLinkUsage.objects.filter(connection_link=link)
        .select_related("social_account")
        .values_list("social_account__account_name", flat=True)
    )
    account_names = ", ".join(connected_accounts) or "No accounts"

    # Notify workspace managers and owners
    managers = WorkspaceMembership.objects.filter(
        workspace=link.workspace,
        workspace_role__in=[
            WorkspaceMembership.WorkspaceRole.OWNER,
            WorkspaceMembership.WorkspaceRole.MANAGER,
        ],
    ).select_related("user")

    for membership in managers:
        notify(
            user=membership.user,
            event_type=EventType.CLIENT_CONNECTED_ACCOUNTS,
            title="Client connected accounts",
            body=f"{connected_count} account(s) connected to {link.workspace.name}: {account_names}",
            data={
                "workspace_id": str(link.workspace_id),
                "connection_link_id": str(link.id),
            },
        )

    return render(
        request,
        "onboarding/connection_success.html",
        {
            "workspace": link.workspace,
            "org": link.workspace.organization,
            "connected_count": connected_count,
        },
    )


@require_POST
def connection_bluesky_connect(request, token):
    """Connect a Bluesky account via the connection link page."""
    link = _get_connection_link_or_none(token)
    if not link or not link.is_active:
        return render(request, "onboarding/connection_expired.html", status=400)

    handle = request.POST.get("handle", "").strip()
    app_password = request.POST.get("app_password", "").strip()

    if not handle or not app_password:
        request.session["connection_link_error"] = "Handle and app password are required."
        return redirect("onboarding:connection_page", token=token)

    org = link.workspace.organization

    try:
        provider = _get_provider_for_platform(PlatformCredential.Platform.BLUESKY, org.id)
        tokens = provider.create_session(handle, app_password)
        profile = provider.get_profile(tokens.access_token)

        account = _create_or_update_account(
            workspace_id=str(link.workspace_id),
            platform=PlatformCredential.Platform.BLUESKY,
            profile=profile,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            instance_url=provider.pds_url,
        )
        ConnectionLinkUsage.objects.get_or_create(
            connection_link=link,
            social_account=account,
        )

    except Exception:
        logger.exception("Connection link Bluesky connection failed")
        request.session["connection_link_error"] = (
            "Failed to connect Bluesky account. Check your handle and app password."
        )

    return redirect("onboarding:connection_page", token=token)


@csp_update(FORM_ACTION="'self' https:")
@require_POST
def connection_mastodon_start(request, token):
    """Initiate Mastodon OAuth from the connection link page."""
    link = _get_connection_link_or_none(token)
    if not link or not link.is_active:
        return render(request, "onboarding/connection_expired.html", status=400)

    instance_url = _normalize_mastodon_instance_url(request.POST.get("instance_url", ""))
    if not instance_url:
        request.session["connection_link_error"] = "Instance URL is required."
        return redirect("onboarding:connection_page", token=token)

    org = link.workspace.organization

    from apps.social_accounts.models import MastodonAppRegistration

    # Check for existing or create app registration
    try:
        registration = MastodonAppRegistration.objects.get(instance_url=instance_url)
        client_id = registration.client_id
        client_secret = registration.client_secret
    except MastodonAppRegistration.DoesNotExist:
        try:
            provider = _get_provider_for_platform(
                PlatformCredential.Platform.MASTODON,
                org.id,
                instance_url=instance_url,
            )
            redirect_uri = _build_connection_redirect_uri(request, PlatformCredential.Platform.MASTODON)
            app_data = provider.register_app(instance_url, redirect_uri)
            MastodonAppRegistration.objects.create(
                instance_url=instance_url,
                client_id=app_data["client_id"],
                client_secret=app_data["client_secret"],
            )
            client_id = app_data["client_id"]
            client_secret = app_data["client_secret"]
        except Exception:
            logger.exception("Mastodon app registration failed for %s", instance_url)
            request.session["connection_link_error"] = f"Failed to register with {instance_url}. Check the URL."
            return redirect("onboarding:connection_page", token=token)

    # Initiate OAuth
    provider = _get_provider_for_platform(
        PlatformCredential.Platform.MASTODON,
        org.id,
        instance_url=instance_url,
        client_id=client_id,
        client_secret=client_secret,
    )

    nonce = secrets.token_urlsafe(32)
    state = _sign_connection_link_state(
        link.workspace_id,
        PlatformCredential.Platform.MASTODON,
        token,
        nonce,
    )

    request.session[CONNECTION_LINK_OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(link.workspace_id),
        "platform": PlatformCredential.Platform.MASTODON,
        "token": token,
        "instance_url": instance_url,
    }

    redirect_uri = _build_connection_redirect_uri(request, PlatformCredential.Platform.MASTODON)
    auth_url = provider.get_auth_url(redirect_uri, state)
    return redirect(auth_url)
