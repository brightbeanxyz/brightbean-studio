"""Social account connection views.

Handles OAuth flows, account listing, connect/reconnect/disconnect actions.
"""

import logging
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from apps.common.validators import is_safe_url as _is_safe_url
from apps.credentials.models import PlatformCredential
from apps.members.decorators import require_permission

from .models import MastodonAppRegistration, PlatformVisibility, SocialAccount

logger = logging.getLogger(__name__)

OAUTH_STATE_MAX_AGE = 600  # 10 minutes
OAUTH_SESSION_KEY = "social_oauth"


def _get_provider_for_platform(platform: str, org_id, **extra_credentials):
    """Resolve app credentials and instantiate the provider."""
    from providers import get_provider

    # Try org-specific credentials first, then env fallback
    try:
        cred = PlatformCredential.objects.for_org(org_id).get(platform=platform, is_configured=True)
        credentials = cred.credentials
    except PlatformCredential.DoesNotExist:
        env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
        credentials = env_creds.get(platform, {})

    if extra_credentials:
        credentials = {**credentials, **extra_credentials}

    return get_provider(platform, credentials)


def _get_visible_platform_choices():
    """Return PlatformCredential.Platform.choices filtered to visible platforms.

    Platforms without a PlatformVisibility row default to visible.
    """
    hidden = set(PlatformVisibility.objects.filter(is_visible=False).values_list("platform", flat=True))
    return [(value, label) for value, label in PlatformCredential.Platform.choices if value not in hidden]


def _get_configured_platforms(org_id):
    """Return set of platform names that have credentials configured."""
    from providers import PROVIDER_REGISTRY
    from providers.types import AuthType

    configured = set(
        PlatformCredential.objects.for_org(org_id).filter(is_configured=True).values_list("platform", flat=True)
    )
    env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
    for platform, creds in env_creds.items():
        if any(v for v in creds.values()):
            configured.add(platform)

    # Session-auth platforms (e.g. Bluesky) don't need app-level credentials —
    # the user supplies their own handle + app password at connect time.
    # Instance-OAuth platforms (e.g. Mastodon) don't need them either —
    # we register a per-instance OAuth app on first connect and persist it in
    # MastodonAppRegistration.
    for platform, provider_cls in PROVIDER_REGISTRY.items():
        if provider_cls().auth_type in (AuthType.SESSION, AuthType.INSTANCE_OAUTH):
            configured.add(platform)

    return configured


def _build_redirect_uri(request, platform):
    """Build the OAuth callback URL."""
    from django.urls import reverse

    return request.build_absolute_uri(reverse("social_accounts:oauth_callback", kwargs={"platform": platform}))


def _sign_state(workspace_id, platform, user_id, nonce):
    """Create a signed OAuth state parameter."""
    return signing.dumps(
        {
            "workspace_id": str(workspace_id),
            "platform": platform,
            "user_id": str(user_id),
            "nonce": nonce,
        },
        salt="social-oauth-state",
    )


def _unsign_state(state_str):
    """Verify and decode the OAuth state parameter."""
    return signing.loads(
        state_str,
        salt="social-oauth-state",
        max_age=OAUTH_STATE_MAX_AGE,
    )


def _normalize_mastodon_instance_url(raw):
    """Normalize user-supplied Mastodon instance input to `scheme://host[:port]`.

    Accepts: bare hosts (`mastodon.social`), URLs with paths (`https://mastodon.social/@user`),
    fediverse handles (`@user@mastodon.social`, `user@mastodon.social`), and values with
    extra whitespace or trailing slashes. Defaults the scheme to https when missing.
    Returns an empty string when the input has no host.
    """
    value = (raw or "").strip()
    if not value:
        return ""

    # Fediverse handle form: `@user@host` or `user@host`. If there's exactly one '@'
    # and no scheme, treat it as a handle and extract the host. Two '@'s means a
    # leading '@' plus user@host.
    if "://" not in value and "@" in value:
        parts = value.lstrip("@").split("@")
        if len(parts) == 2 and parts[1]:
            value = parts[1]

    if "://" not in value:
        value = f"https://{value}"

    parts = urlsplit(value)
    if not parts.netloc:
        return ""
    scheme = parts.scheme or "https"
    return f"{scheme}://{parts.netloc}"


def _resolve_mastodon_extra_creds(session_data):
    """Resolve Mastodon instance-specific credentials from the OAuth session.

    Returns a dict suitable for `_get_provider_for_platform(**extra_creds)`
    containing `instance_url`, and `client_id`/`client_secret` when a matching
    `MastodonAppRegistration` exists. Empty dict when no instance_url is set.
    """
    extra_creds: dict = {}
    instance_url = (session_data or {}).get("instance_url", "")
    if not instance_url:
        return extra_creds

    extra_creds["instance_url"] = instance_url
    try:
        reg = MastodonAppRegistration.objects.get(instance_url=instance_url)
        extra_creds["client_id"] = reg.client_id
        extra_creds["client_secret"] = reg.client_secret
    except MastodonAppRegistration.DoesNotExist:
        pass
    return extra_creds


# ------------------------------------------------------------------
# Account List
# ------------------------------------------------------------------


@login_required
@require_permission("manage_social_accounts")
def account_list(request, workspace_id):
    """List connected social accounts for a workspace."""
    accounts = (
        SocialAccount.objects.for_workspace(workspace_id)
        .prefetch_related("posting_slots")
        .order_by("platform", "account_name")
    )
    configured_platforms = _get_configured_platforms(request.org.id)

    return render(
        request,
        "social_accounts/list.html",
        {
            "accounts": accounts,
            "workspace_id": workspace_id,
            "configured_platforms": configured_platforms,
            "platform_choices": PlatformCredential.Platform.choices,
            "settings_active": "social_accounts",
        },
    )


# ------------------------------------------------------------------
# Connect Platform (OAuth redirect)
# ------------------------------------------------------------------


@csp_update(
    FORM_ACTION="'self' https://accounts.google.com https://www.facebook.com https://api.instagram.com https://www.instagram.com https://threads.net https://www.linkedin.com https://www.pinterest.com https://www.tiktok.com"
)
@login_required
@require_permission("manage_social_accounts")
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def connect_platform(request, workspace_id):
    """GET: show platform grid. POST: initiate OAuth flow."""
    configured_platforms = _get_configured_platforms(request.org.id)
    visible_platform_choices = _get_visible_platform_choices()

    if request.method == "GET":
        return render(
            request,
            "social_accounts/connect.html",
            {
                "workspace_id": workspace_id,
                "platform_choices": visible_platform_choices,
                "configured_platforms": configured_platforms,
            },
        )

    # POST: initiate OAuth
    platform = request.POST.get("platform", "").strip()
    if platform not in dict(visible_platform_choices):
        messages.error(request, "This platform is not available.")
        return redirect("social_accounts:connect", workspace_id=workspace_id)

    if platform not in configured_platforms:
        messages.error(
            request,
            f"Platform credentials for {platform} are not configured. Please contact your administrator.",
        )
        return redirect("social_accounts:connect", workspace_id=workspace_id)

    # Special auth flows
    if platform == PlatformCredential.Platform.BLUESKY:
        return redirect("social_accounts:connect_bluesky", workspace_id=workspace_id)
    if platform == PlatformCredential.Platform.MASTODON:
        return redirect("social_accounts:connect_mastodon", workspace_id=workspace_id)

    # Standard OAuth flow
    provider = _get_provider_for_platform(platform, request.org.id)
    nonce = secrets.token_urlsafe(32)
    state = _sign_state(workspace_id, platform, request.user.id, nonce)

    # Store nonce in session to prevent replay
    request.session[OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(workspace_id),
        "platform": platform,
    }

    redirect_uri = _build_redirect_uri(request, platform)
    auth_url = provider.get_auth_url(redirect_uri, state)
    return redirect(auth_url)


# ------------------------------------------------------------------
# OAuth Callback
# ------------------------------------------------------------------


@login_required
@ratelimit(key="user", rate="20/m", block=True)
@require_GET
def oauth_callback(request, platform):
    """Handle OAuth callback from the platform."""
    error = request.GET.get("error")
    if error:
        error_desc = request.GET.get("error_description", error)
        messages.error(request, f"OAuth error: {error_desc}")
        session_data = request.session.pop(OAUTH_SESSION_KEY, {})
        workspace_id = session_data.get("workspace_id")
        if workspace_id:
            return redirect("calendar:calendar", workspace_id=workspace_id)
        return redirect("dashboard")

    code = request.GET.get("code")
    state_str = request.GET.get("state")

    if not code or not state_str:
        messages.error(request, "Missing authorization code or state parameter.")
        return redirect("dashboard")

    # Validate state
    try:
        state_data = _unsign_state(state_str)
    except signing.BadSignature:
        messages.error(request, "Invalid or expired OAuth state. Please try again.")
        return redirect("dashboard")

    # Validate nonce from session
    session_data = request.session.pop(OAUTH_SESSION_KEY, {})
    if not session_data or session_data.get("nonce") != state_data.get("nonce"):
        messages.error(request, "OAuth session mismatch. Please try again.")
        return redirect("dashboard")

    # Validate platform matches
    if state_data.get("platform") != platform:
        messages.error(request, "Platform mismatch in OAuth callback.")
        return redirect("dashboard")

    # Validate user
    if str(request.user.id) != state_data.get("user_id"):
        raise PermissionDenied("OAuth state does not match current user.")

    workspace_id = state_data["workspace_id"]

    # Re-check workspace membership - user may have lost access during OAuth
    from apps.members.models import WorkspaceMembership

    ws_membership = WorkspaceMembership.objects.filter(user=request.user, workspace_id=workspace_id).first()
    if not ws_membership:
        raise PermissionDenied("You no longer have access to this workspace.")
    perms = ws_membership.effective_permissions
    if not perms.get("manage_social_accounts", False):
        raise PermissionDenied("You no longer have permission to manage social accounts.")

    try:
        # For Mastodon, we need instance-specific credentials from session + registration
        extra_creds: dict = {}
        if platform == PlatformCredential.Platform.MASTODON:
            extra_creds = _resolve_mastodon_extra_creds(session_data)

        provider = _get_provider_for_platform(platform, request.org.id, **extra_creds)
        redirect_uri = _build_redirect_uri(request, platform)
        tokens = provider.exchange_code(code, redirect_uri)
        profile = provider.get_profile(tokens.access_token)

        # Facebook/Instagram: only connect Pages, not personal profiles
        if platform in (
            PlatformCredential.Platform.FACEBOOK,
            PlatformCredential.Platform.INSTAGRAM,
        ) and hasattr(provider, "get_user_pages"):
            pages = provider.get_user_pages(tokens.access_token)
            if pages:
                # Store in session for account selection
                request.session["oauth_page_select"] = {
                    "workspace_id": workspace_id,
                    "platform": platform,
                    "user_tokens": {
                        "access_token": tokens.access_token,
                        "refresh_token": tokens.refresh_token,
                    },
                    "pages": pages,
                }
                return redirect("social_accounts:select_account")
            else:
                messages.warning(
                    request,
                    "No Facebook Pages were found for your account. "
                    "Only Pages can be connected — personal profiles are not "
                    "supported by the Facebook API. "
                    "If you expected to see a Page, make sure you have admin "
                    "access and try removing the app in Facebook Settings \u2192 "
                    "Business Integrations, then reconnect.",
                )
                return redirect("social_accounts:list", workspace_id=workspace_id)

        # Standard single-account flow (non-Facebook/Instagram platforms)
        _create_or_update_account(
            workspace_id=workspace_id,
            platform=platform,
            profile=profile,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            instance_url=extra_creds.get("instance_url", ""),
        )
        messages.success(request, f"Connected {profile.name} successfully.")

    except (signing.BadSignature, PermissionDenied):
        raise
    except Exception:
        logger.exception("OAuth callback failed for %s", platform)
        messages.error(
            request,
            "Failed to connect account. Please try again.",
        )

    return redirect("calendar:calendar", workspace_id=workspace_id)


# ------------------------------------------------------------------
# Account Selection (Facebook multi-page)
# ------------------------------------------------------------------


@login_required
def select_account(request):
    """Show page/account selection after multi-page OAuth."""
    page_data = request.session.get("oauth_page_select")
    if not page_data:
        messages.error(request, "No accounts to select. Please start over.")
        return redirect("dashboard")

    workspace_id = page_data["workspace_id"]

    if request.method == "GET":
        return render(
            request,
            "social_accounts/account_select.html",
            {
                "pages": page_data["pages"],
                "platform": page_data["platform"],
                "workspace_id": workspace_id,
            },
        )

    # POST: create accounts for selected pages
    selected_ids = request.POST.getlist("selected_pages")
    if not selected_ids:
        messages.error(request, "Please select at least one account.")
        return render(
            request,
            "social_accounts/account_select.html",
            {
                "pages": page_data["pages"],
                "platform": page_data["platform"],
                "workspace_id": workspace_id,
            },
        )

    from providers.types import AccountProfile

    platform = page_data["platform"]
    user_tokens = page_data["user_tokens"]
    connected = []

    for page in page_data["pages"]:
        if page["id"] in selected_ids:
            profile = AccountProfile(
                platform_id=page["id"],
                name=page["name"],
                handle=page.get("handle"),
                avatar_url=page.get("picture", ""),
                follower_count=page.get("followers_count", 0),
            )
            _create_or_update_account(
                workspace_id=workspace_id,
                platform=platform,
                profile=profile,
                access_token=page.get("access_token", user_tokens["access_token"]),
                refresh_token=user_tokens.get("refresh_token"),
                expires_in=None,
            )
            connected.append(page["name"])

    request.session.pop("oauth_page_select", None)

    if connected:
        names = ", ".join(connected)
        messages.success(request, f"Connected: {names}")

    return redirect("calendar:calendar", workspace_id=workspace_id)


# ------------------------------------------------------------------
# Bluesky Connect (session-based, no OAuth)
# ------------------------------------------------------------------


@login_required
@require_permission("manage_social_accounts")
def connect_bluesky(request, workspace_id):
    """Connect a Bluesky account via handle + app password."""
    if request.method == "GET":
        return render(
            request,
            "social_accounts/bluesky_connect.html",
            {"workspace_id": workspace_id},
        )

    handle = request.POST.get("handle", "").strip().lstrip("@")
    app_password = request.POST.get("app_password", "").strip()

    if not handle or not app_password:
        messages.error(request, "Handle and app password are required.")
        return render(
            request,
            "social_accounts/bluesky_connect.html",
            {"workspace_id": workspace_id},
        )

    try:
        provider = _get_provider_for_platform(PlatformCredential.Platform.BLUESKY, request.org.id)
        tokens = provider.create_session(handle, app_password)
        profile = provider.get_profile(tokens.access_token)

        _create_or_update_account(
            workspace_id=workspace_id,
            platform=PlatformCredential.Platform.BLUESKY,
            profile=profile,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            instance_url=provider.pds_url,
        )
        messages.success(request, f"Connected {profile.name} on Bluesky.")

    except Exception:
        logger.exception("Bluesky connection failed")
        messages.error(
            request,
            "Failed to connect Bluesky account. Check your handle and app password.",
        )
        return render(
            request,
            "social_accounts/bluesky_connect.html",
            {"workspace_id": workspace_id},
        )

    return redirect("calendar:calendar", workspace_id=workspace_id)


# ------------------------------------------------------------------
# Mastodon Connect (instance-based OAuth)
# ------------------------------------------------------------------


@csp_update(FORM_ACTION="'self' https:")
@login_required
@require_permission("manage_social_accounts")
def connect_mastodon(request, workspace_id):
    """Connect a Mastodon account via instance URL + OAuth."""
    if request.method == "GET":
        return render(
            request,
            "social_accounts/mastodon_connect.html",
            {"workspace_id": workspace_id},
        )

    instance_url = _normalize_mastodon_instance_url(request.POST.get("instance_url", ""))
    if not instance_url:
        messages.error(request, "Instance URL is required.")
        return render(
            request,
            "social_accounts/mastodon_connect.html",
            {"workspace_id": workspace_id},
        )

    # Validate against SSRF - reject private/reserved IP ranges
    if not _is_safe_url(instance_url):
        messages.error(request, "Invalid instance URL. Private or reserved addresses are not allowed.")
        return render(
            request,
            "social_accounts/mastodon_connect.html",
            {"workspace_id": workspace_id},
        )

    # Check for existing app registration or create one
    try:
        registration = MastodonAppRegistration.objects.get(instance_url=instance_url)
        client_id = registration.client_id
        client_secret = registration.client_secret
    except MastodonAppRegistration.DoesNotExist:
        # Register app on this instance
        try:
            provider = _get_provider_for_platform(
                PlatformCredential.Platform.MASTODON,
                request.org.id,
                instance_url=instance_url,
            )
            redirect_uri = _build_redirect_uri(request, PlatformCredential.Platform.MASTODON)
            app_data = provider.register_app(instance_url, redirect_uri)
            registration = MastodonAppRegistration.objects.create(
                instance_url=instance_url,
                client_id=app_data["client_id"],
                client_secret=app_data["client_secret"],
            )
            client_id = app_data["client_id"]
            client_secret = app_data["client_secret"]
        except Exception:
            logger.exception("Mastodon app registration failed for %s", instance_url)
            messages.error(
                request,
                f"Failed to register with {instance_url}. Check the URL.",
            )
            return render(
                request,
                "social_accounts/mastodon_connect.html",
                {"workspace_id": workspace_id},
            )

    # Initiate OAuth
    provider = _get_provider_for_platform(
        PlatformCredential.Platform.MASTODON,
        request.org.id,
        instance_url=instance_url,
        client_id=client_id,
        client_secret=client_secret,
    )

    nonce = secrets.token_urlsafe(32)
    state = _sign_state(
        workspace_id,
        PlatformCredential.Platform.MASTODON,
        request.user.id,
        nonce,
    )

    request.session[OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(workspace_id),
        "platform": PlatformCredential.Platform.MASTODON,
        "instance_url": instance_url,
    }

    redirect_uri = _build_redirect_uri(request, PlatformCredential.Platform.MASTODON)
    auth_url = provider.get_auth_url(redirect_uri, state)
    return redirect(auth_url)


# ------------------------------------------------------------------
# Reconnect
# ------------------------------------------------------------------


@csp_update(
    FORM_ACTION="'self' https://accounts.google.com https://www.facebook.com https://api.instagram.com https://www.instagram.com https://threads.net https://www.linkedin.com https://www.pinterest.com https://www.tiktok.com"
)
@login_required
@require_permission("manage_social_accounts")
@require_POST
def reconnect(request, workspace_id, account_id):
    """Re-initiate OAuth for an existing account."""
    account = get_object_or_404(SocialAccount.objects.for_workspace(workspace_id), id=account_id)
    platform = account.platform

    if platform == PlatformCredential.Platform.BLUESKY:
        return redirect("social_accounts:connect_bluesky", workspace_id=workspace_id)
    if platform == PlatformCredential.Platform.MASTODON:
        return redirect("social_accounts:connect_mastodon", workspace_id=workspace_id)

    # Standard OAuth reconnect
    provider = _get_provider_for_platform(platform, request.org.id)
    nonce = secrets.token_urlsafe(32)
    state = _sign_state(workspace_id, platform, request.user.id, nonce)

    request.session[OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(workspace_id),
        "platform": platform,
    }

    redirect_uri = _build_redirect_uri(request, platform)
    auth_url = provider.get_auth_url(redirect_uri, state)
    return redirect(auth_url)


# ------------------------------------------------------------------
# Disconnect
# ------------------------------------------------------------------


@login_required
@require_permission("manage_social_accounts")
@require_POST
def disconnect(request, workspace_id, account_id):
    """Disconnect a social account."""
    account = get_object_or_404(SocialAccount.objects.for_workspace(workspace_id), id=account_id)

    # Try to revoke token
    try:
        provider = _get_provider_for_platform(account.platform, request.org.id)
        if account.oauth_access_token:
            provider.revoke_token(account.oauth_access_token)
    except Exception:
        logger.warning(
            "Failed to revoke token for %s, proceeding with disconnect",
            account,
        )

    # Delete posts that ONLY target this account (will be fully orphaned).
    # Multi-platform posts keep their other PlatformPost targets via cascade.
    from django.db.models import Count

    from apps.composer.models import PlatformPost, Post

    orphan_post_ids = list(
        PlatformPost.objects.filter(social_account=account)
        .values("post_id")
        .annotate(total_platforms=Count("post__platform_posts"))
        .filter(total_platforms=1)
        .values_list("post_id", flat=True)
    )
    if orphan_post_ids:
        Post.objects.filter(id__in=orphan_post_ids).delete()

    account_name = account.account_name or account.account_handle
    account.delete()

    messages.success(request, f"Disconnected {account_name}.")

    # HTMX partial response
    if request.headers.get("HX-Request"):
        return render(request, "social_accounts/partials/_empty.html")

    return redirect("social_accounts:list", workspace_id=workspace_id)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _create_or_update_account(
    *,
    workspace_id,
    platform,
    profile,
    access_token,
    refresh_token=None,
    expires_in=None,
    instance_url="",
):
    """Create or update a SocialAccount from OAuth results."""
    token_expires_at = None
    if expires_in:
        token_expires_at = timezone.now() + timedelta(seconds=expires_in)

    account, created = SocialAccount.objects.update_or_create(
        workspace_id=workspace_id,
        platform=platform,
        account_platform_id=profile.platform_id,
        defaults={
            "account_name": profile.name,
            "account_handle": profile.handle or "",
            "avatar_url": profile.avatar_url or "",
            "follower_count": profile.follower_count,
            "oauth_access_token": access_token,
            "oauth_refresh_token": refresh_token or "",
            "token_expires_at": token_expires_at,
            "instance_url": instance_url,
            "connection_status": SocialAccount.ConnectionStatus.CONNECTED,
            "last_error": "",
        },
    )

    if created:
        from apps.calendar.services import create_default_queue_and_slots

        create_default_queue_and_slots(account)

    return account
