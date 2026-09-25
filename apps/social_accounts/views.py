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
from apps.credentials.models import PlatformCredential, derive_is_configured
from apps.members.decorators import require_permission
from providers.exceptions import QuotaExceededError

from .error_messages import quota_connect_error
from .models import MastodonAppRegistration, PlatformVisibility, SocialAccount
from .oauth_aliases import from_url_slug, redirect_uri_from_request, to_url_slug
from .oauth_pkce import issue_pkce_verifier, pkce_kwargs
from .provider_factory import _get_provider_for_platform, apply_analytics_scope_flag
from .webhooks import (
    subscribe_account_webhooks,
    subscribe_account_webhooks_task,
    unsubscribe_account_webhooks,
)

logger = logging.getLogger(__name__)

OAUTH_STATE_MAX_AGE = 600  # 10 minutes
OAUTH_SESSION_KEY = "social_oauth"


def _get_visible_platform_choices():
    """Return PlatformCredential.Platform.choices filtered to visible platforms.

    Platforms without a PlatformVisibility row default to visible.
    """
    return PlatformVisibility.visible_choices()


def _get_configured_platforms(org_id):
    """Return set of platform names that have credentials configured."""
    from providers import PROVIDER_REGISTRY
    from providers.types import AuthType

    configured = set(
        PlatformCredential.objects.for_org(org_id).filter(is_configured=True).values_list("platform", flat=True)
    )
    env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
    for platform, creds in env_creds.items():
        # Same completeness rule the credential resolver applies, so the grid can
        # never offer a Connect button that resolution will reject. A truthiness
        # check here would let a half-filled pair (app id set, secret missing)
        # render as connectable, walk the user through the platform's consent
        # screen, and only fail at token exchange with a generic error.
        if derive_is_configured(platform, creds):
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
    """Build the OAuth callback URL.

    Platforms with an entry in ``PLATFORM_TO_URL_ALIAS`` (currently only
    TikTok → ``social1``) use the opaque slug in the URL path so the
    redirect URI doesn't contain the platform brand name. The signed
    OAuth state still carries the real platform identifier.
    """
    from django.urls import reverse

    url_slug = to_url_slug(platform)
    return request.build_absolute_uri(reverse("social_accounts:oauth_callback", kwargs={"platform": url_slug}))


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
    if platform == PlatformCredential.Platform.DEVTO:
        return redirect("social_accounts:connect_devto", workspace_id=workspace_id)

    # Standard OAuth flow
    provider = _get_provider_for_platform(platform, request.org.id)
    apply_analytics_scope_flag(provider, platform)
    nonce = secrets.token_urlsafe(32)
    state = _sign_state(workspace_id, platform, request.user.id, nonce)

    # PKCE verifier (e.g. TikTok); round-trips via the session alongside the nonce.
    code_verifier = issue_pkce_verifier(provider)

    # Store nonce in session to prevent replay
    request.session[OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(workspace_id),
        "platform": platform,
        "code_verifier": code_verifier,
    }

    redirect_uri = _build_redirect_uri(request, platform)
    auth_url = provider.get_auth_url(redirect_uri, state, **pkce_kwargs(code_verifier))
    return redirect(auth_url)


# ------------------------------------------------------------------
# OAuth Callback
# ------------------------------------------------------------------


@login_required
@ratelimit(key="user", rate="20/m", block=True)
@require_GET
def oauth_callback(request, platform):
    """Handle OAuth callback from the platform.

    ``platform`` arrives as the URL slug, which may be an alias (e.g.
    ``social1`` for TikTok). Normalise it before any platform-keyed lookup
    or comparison against the signed state.
    """
    platform = from_url_slug(platform)
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
        redirect_uri = redirect_uri_from_request(request)
        tokens = provider.exchange_code(code, redirect_uri, **pkce_kwargs(session_data.get("code_verifier")))

        # Facebook/Instagram/LinkedIn Company: connect Pages, not personal profiles
        if platform in (
            PlatformCredential.Platform.FACEBOOK,
            PlatformCredential.Platform.INSTAGRAM,
            PlatformCredential.Platform.LINKEDIN_COMPANY,
        ) and hasattr(provider, "get_user_pages"):
            tokens, promoted = promote_meta_user_token(provider, platform, tokens)
            pages = provider.get_user_pages(tokens.access_token)
            if pages:
                # Filtered by workspace only: that set is bounded by what this
                # workspace has connected, while the page list is bounded only
                # by how many Pages the login administers — passing every page
                # id back as an IN clause scales with the wrong number.
                existing_ids = set(
                    SocialAccount.objects.filter(
                        workspace_id=workspace_id,
                        platform=platform,
                    ).values_list("account_platform_id", flat=True)
                )
                for page in pages:
                    page["already_connected"] = page["id"] in existing_ids
                # Store in session for account selection
                request.session["oauth_page_select"] = {
                    "workspace_id": workspace_id,
                    "platform": platform,
                    "user_tokens": {
                        "access_token": tokens.access_token,
                        "refresh_token": tokens.refresh_token,
                        # None once promoted: a Page token derived from a
                        # long-lived user token does not expire. On the fallback
                        # path it is the short-lived expiry, which the account
                        # must carry to be seen as expiring at all.
                        "expires_in": None if promoted else tokens.expires_in,
                    },
                    "pages": pages,
                }
                return redirect("social_accounts:select_account")
            else:
                if platform == PlatformCredential.Platform.LINKEDIN_COMPANY:
                    warning = (
                        "No LinkedIn Company Pages were found for your account. "
                        "Only Company Pages you administer can be connected — "
                        "personal profiles connect via the LinkedIn (Personal) option. "
                        "If you expected to see a Page, ask the page owner to grant "
                        "you Admin access in LinkedIn \u2192 Admin tools \u2192 "
                        "Manage admins, then reconnect."
                    )
                else:
                    if platform == PlatformCredential.Platform.INSTAGRAM:
                        warning = (
                            "No Instagram Business accounts were found for your account. "
                            "Only Instagram Business or Creator accounts linked to a Facebook Page "
                            "can be connected through this Instagram option. If you expected to "
                            "see an account, make sure it is linked to a Page you manage, then reconnect."
                        )
                    else:
                        warning = (
                            "No Facebook Pages were found for your account. "
                            "Only Pages can be connected — personal profiles are not "
                            "supported by the Facebook API. "
                            "If you expected to see a Page, make sure you have admin "
                            "access and try removing the app in Facebook Settings \u2192 "
                            "Business Integrations, then reconnect."
                        )
                messages.warning(request, warning)
                return redirect("social_accounts:list", workspace_id=workspace_id)

        # Standard single-account flow (non-Facebook/Instagram platforms)
        profile = provider.get_profile(tokens.access_token)
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
    except QuotaExceededError as exc:
        # Before the blanket clause below, whose "Please try again" is the one
        # piece of advice that cannot work here: the grant is fine, the
        # platform's daily budget is spent, and every retry until the window
        # rolls over fails identically. This is what a user connecting a
        # YouTube channel at 03:00 UTC was being told to keep doing.
        logger.warning("OAuth callback hit a spent %s quota: %s", platform, exc)
        messages.error(request, quota_connect_error(exc))
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

    def _render_picker():
        # Resolve publishability here rather than in the template: Django
        # resolves a missing key to string_if_invalid, so `can_publish is False`
        # in markup is a different predicate from the Python one and would drift
        # from it. The template gets a plain bool it can trust.
        rows = [{**page, "can_publish": page_is_publishable(page)} for page in page_data["pages"]]
        return render(
            request,
            "social_accounts/account_select.html",
            {
                "pages": rows,
                "platform": page_data["platform"],
                "workspace_id": workspace_id,
            },
        )

    if request.method == "GET":
        return _render_picker()

    # POST: create accounts for selected pages
    selected_ids = request.POST.getlist("selected_pages")
    if not selected_ids:
        messages.error(request, "Please select at least one account.")
        return _render_picker()

    from providers.types import AccountProfile

    platform = page_data["platform"]
    user_tokens = page_data["user_tokens"]
    connected = []

    for page in page_data["pages"]:
        if page["id"] in selected_ids:
            if not page_is_publishable(page):
                # Meta reported the Page's task list and it lacks CREATE_CONTENT.
                # The template already disables these rows; this guard is what
                # stops a hand-built POST from connecting an account that would
                # fail every publish.
                messages.error(
                    request,
                    f"Could not connect {page['name']}: your Facebook access cannot create content for this Page.",
                )
                continue
            access_token = resolve_page_account_token(page, platform, user_tokens.get("access_token", ""))
            if not access_token:
                messages.error(
                    request,
                    f"Could not connect {page['name']}: the platform did not provide an account token.",
                )
                continue

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
                access_token=access_token,
                refresh_token=user_tokens.get("refresh_token"),
                expires_in=user_tokens.get("expires_in"),
                # Instagram-via-Facebook receives its webhooks through the
                # linked Page, so remember which Page to subscribe.
                webhook_target_id=page.get("page_id", ""),
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
# DEV.to Connect (API-key based, no OAuth)
# ------------------------------------------------------------------


@login_required
@require_permission("manage_social_accounts")
def connect_devto(request, workspace_id):
    """Connect a DEV.to account via a personal API key."""
    if request.method == "GET":
        return render(
            request,
            "social_accounts/devto_connect.html",
            {"workspace_id": workspace_id},
        )

    api_key = request.POST.get("api_key", "").strip()
    if not api_key:
        messages.error(request, "A DEV.to API key is required.")
        return render(
            request,
            "social_accounts/devto_connect.html",
            {"workspace_id": workspace_id},
        )

    try:
        provider = _get_provider_for_platform(PlatformCredential.Platform.DEVTO, request.org.id)
        profile = provider.get_profile(api_key)
        _create_or_update_account(
            workspace_id=workspace_id,
            platform=PlatformCredential.Platform.DEVTO,
            profile=profile,
            access_token=api_key,
        )
        messages.success(request, f"Connected {profile.name} on DEV.to.")
    except Exception:
        logger.exception("DEV.to connection failed")
        messages.error(request, "Failed to connect DEV.to account. Check your API key.")
        return render(request, "social_accounts/devto_connect.html", {"workspace_id": workspace_id})

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
    if platform == PlatformCredential.Platform.DEVTO:
        return redirect("social_accounts:connect_devto", workspace_id=workspace_id)

    # Standard OAuth reconnect
    provider = _get_provider_for_platform(platform, request.org.id)
    apply_analytics_scope_flag(provider, platform)
    nonce = secrets.token_urlsafe(32)
    state = _sign_state(workspace_id, platform, request.user.id, nonce)
    code_verifier = issue_pkce_verifier(provider)

    request.session[OAUTH_SESSION_KEY] = {
        "nonce": nonce,
        "workspace_id": str(workspace_id),
        "platform": platform,
        "code_verifier": code_verifier,
    }

    redirect_uri = _build_redirect_uri(request, platform)
    auth_url = provider.get_auth_url(redirect_uri, state, **pkce_kwargs(code_verifier))
    return redirect(auth_url)


@login_required
@require_permission("manage_social_accounts")
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def retry_webhooks(request, workspace_id, account_id):
    """Re-run a failed webhook subscription without a new OAuth grant.

    A subscription can fail for reasons that have nothing to do with the token —
    a transient Graph error, or a bug in what we asked for — and sending the
    user through the full OAuth dance to retry one API call is theatre. Runs
    inline rather than through ``subscribe_account_webhooks_task``: that task
    exists so connecting *several* Pages at once doesn't stack a round trip per
    Page inside the redirect the user is waiting on, which a single deliberate
    retry doesn't. Rate limited because each press is a live round trip to the
    platform on a request thread.
    """
    account = get_object_or_404(SocialAccount.objects.for_workspace(workspace_id), id=account_id)

    # A dead connection cannot carry a subscription: the call would spend a
    # round trip to be rejected, then overwrite the warning with one about
    # real-time delivery when the real problem is the connection itself. Gated
    # on the same ``needs_reconnect`` the card uses to hide the retry button, so
    # this can only be reached by a stale card or a direct POST — and answers
    # both with the reconnect state rather than an unchanged card.
    if account.needs_reconnect:
        if request.headers.get("HX-Request"):
            return _render_account_card(request, account, workspace_id)
        messages.error(request, f"Reconnect {account.display_label} first — its connection isn't healthy.")
        return redirect("social_accounts:list", workspace_id=workspace_id)

    # An explicit press is a fresh mandate: clear the automatic retry budget so
    # a user can always get one more attempt out of a capped-out account.
    SocialAccount.objects.filter(pk=account.pk).update(webhook_retry_count=0)
    account.webhook_retry_count = 0

    subscribed = subscribe_account_webhooks(account)
    account.refresh_from_db()

    if request.headers.get("HX-Request"):
        return _render_account_card(request, account, workspace_id)

    if subscribed:
        messages.success(request, f"Real-time updates are back on for {account.display_label}.")
    else:
        messages.error(request, account.webhook_error or "Couldn't set up real-time updates. Please try again.")
    return redirect("social_accounts:list", workspace_id=workspace_id)


def _render_account_card(request, account, workspace_id):
    """Render one account card for an htmx ``outerHTML`` swap of ``#account-<id>``."""
    return render(
        request,
        "social_accounts/partials/_account_card.html",
        {"account": account, "workspace_id": workspace_id},
    )


# ------------------------------------------------------------------
# Disconnect
# ------------------------------------------------------------------


@login_required
@require_permission("manage_social_accounts")
@require_POST
def disconnect(request, workspace_id, account_id):
    """Disconnect a social account."""
    account = get_object_or_404(SocialAccount.objects.for_workspace(workspace_id), id=account_id)

    # Stop the platform pushing us this account's activity before we drop the
    # token that would let us unsubscribe.
    if account.oauth_access_token:
        unsubscribe_account_webhooks(account)

    # Try to revoke token. The account's own credentials, not just the org's:
    # a Mastodon grant lives on the account's instance, under that instance's
    # app registration, and revoking without them calls an empty base URL.
    try:
        from apps.publisher.engine import _resolve_publish_credentials
        from providers import get_provider

        provider = get_provider(account.platform, _resolve_publish_credentials(account))
        if account.revocation_token:
            provider.revoke_token(account.revocation_token)
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


def promote_meta_user_token(provider, platform, tokens) -> tuple[object, bool]:
    """Trade a Meta authorization-code token for a long-lived one, if we can.

    Returns ``(tokens, promoted)``. ``promoted`` is what callers must key the
    stored expiry off: a Page token derived from a *long-lived* user token does
    not expire and should be stored with no expiry at all, while one derived
    from the short-lived token we fell back to expires within the hour and has
    to carry that expiry or the health and publish checks will never look at it.

    Meta's code exchange returns a *short-lived* user token, and every Page
    token derived from it inherits that lifetime — which is how an agency
    onboarding fifty Pages ends up with fifty credentials that expire before
    the first scheduled post runs. Exchanging first yields durable Page tokens.

    Best-effort on purpose. The exchange can fail for reasons that say nothing
    about whether the grant is usable (a transient Graph 5xx, an app secret the
    deployment has rotated), and the callback's error handling turns any raise
    into "Failed to connect account". A short-lived token still connects and
    still publishes today, so a failure here degrades the connection's lifetime
    rather than blocking it.
    """
    if platform not in (
        PlatformCredential.Platform.FACEBOOK,
        PlatformCredential.Platform.INSTAGRAM,
    ):
        return tokens, False
    try:
        return provider.refresh_token(tokens.access_token), True
    except Exception:
        # Deliberately broad. SocialProvider._request only converts HTTP status
        # codes into ProviderError — httpx transport failures (connect, read
        # timeout) propagate unwrapped, and a timeout is the likeliest
        # transient of all. Catching only ProviderError would let exactly the
        # case this fallback exists for reach the callback's error handler and
        # fail a connect that the short-lived token would have completed.
        logger.warning(
            "Could not exchange the %s user token for a long-lived one; continuing with the short-lived token.",
            platform,
            exc_info=True,
        )
        return tokens, False


def page_is_publishable(page: dict) -> bool:
    """Whether a Page dict from ``get_user_pages`` may be connected.

    The providers compute ``can_publish`` from Meta's per-Page task list; this
    is the single reading of that flag every caller must share. Absent means a
    provider that does not report publishability at all (LinkedIn Company), not
    "no".

    Kept beside ``resolve_page_account_token`` for the same reason that one
    exists: the interactive picker and the connection-link flow had each written
    their own copy of a page-eligibility rule once already, and diverged.
    """
    return page.get("can_publish", True) is not False


def resolve_page_account_token(page: dict, platform: str, user_access_token: str) -> str:
    """Pick the token a Page-backed account must be driven by.

    A Facebook Page needs its *own* Page token: a user token publishes under
    the wrong identity, and — because the only revoke endpoint that accepts it
    revokes the app for the whole person — makes a per-account disconnect able
    to sever every other connection they have.

    Instagram-via-Facebook is the one exception: its calls address the IG user,
    so the user token is the correct credential when the Page dict carries none.

    Returns "" when no usable token exists, which callers must treat as "cannot
    connect this account" rather than substituting one.
    """
    token = page.get("access_token")
    if not token and platform == PlatformCredential.Platform.INSTAGRAM:
        token = user_access_token
    return token or ""


def _create_or_update_account(
    *,
    workspace_id,
    platform,
    profile,
    access_token,
    refresh_token=None,
    expires_in=None,
    instance_url="",
    webhook_target_id="",
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
            "webhook_target_id": webhook_target_id or "",
            "connection_status": SocialAccount.ConnectionStatus.CONNECTED,
            "last_error": "",
            # Fresh OAuth grant invalidates any prior analytics-scope failure.
            "analytics_needs_reconnect": False,
            # Likewise the webhook verdict: the subscription is about to be
            # retried below, and subscribe_account_webhooks returns early
            # without recording when the provider has no webhooks at all — so
            # without this reset a stale failure would outlive the reconnect
            # that was supposed to clear it.
            "webhooks_active": None,
            "webhook_error": "",
            "webhook_needs_reconnect": False,
            "webhook_error_detail": "",
            "webhook_retry_count": 0,
        },
    )

    if created:
        from apps.calendar.services import create_default_queue_and_slots

        create_default_queue_and_slots(account)

    subscribe_account_webhooks_task(str(account.id))

    return account
