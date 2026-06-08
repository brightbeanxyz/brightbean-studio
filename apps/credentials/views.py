from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.members.decorators import require_org_role
from apps.members.models import OrgMembership
from apps.social_accounts.oauth_aliases import to_url_slug

from .models import PlatformCredential


@dataclass(frozen=True)
class CredentialField:
    name: str
    label: str
    secret: bool = True


@dataclass(frozen=True)
class CredentialGroup:
    key: str
    title: str
    platforms: tuple[str, ...]
    fields: tuple[CredentialField, ...]
    description: str
    docs_hint: str = ""

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)


CREDENTIAL_GROUPS: tuple[CredentialGroup, ...] = (
    CredentialGroup(
        key="meta",
        title="Meta",
        platforms=(
            PlatformCredential.Platform.FACEBOOK,
            PlatformCredential.Platform.INSTAGRAM,
            PlatformCredential.Platform.THREADS,
        ),
        fields=(
            CredentialField("app_id", "App ID"),
            CredentialField("app_secret", "App Secret"),
        ),
        description="Enables Facebook Pages, Instagram accounts linked to a Facebook Page, and Threads.",
        docs_hint="Use the Facebook Login redirect URIs shown below for each platform.",
    ),
    CredentialGroup(
        key="instagram_login",
        title="Instagram (Direct)",
        platforms=(PlatformCredential.Platform.INSTAGRAM_LOGIN,),
        fields=(
            CredentialField("app_id", "Instagram App ID"),
            CredentialField("app_secret", "Instagram App Secret"),
        ),
        description="Instagram Login for Professional Instagram accounts without a linked Facebook Page.",
        docs_hint="Use the Instagram Login app credentials, not the Facebook app credentials.",
    ),
    CredentialGroup(
        key="linkedin_personal",
        title="LinkedIn Personal",
        platforms=(PlatformCredential.Platform.LINKEDIN_PERSONAL,),
        fields=(
            CredentialField("client_id", "Client ID"),
            CredentialField("client_secret", "Client Secret"),
        ),
        description="Personal-profile posting via Sign in with LinkedIn and Share on LinkedIn.",
    ),
    CredentialGroup(
        key="linkedin_company",
        title="LinkedIn Company",
        platforms=(PlatformCredential.Platform.LINKEDIN_COMPANY,),
        fields=(
            CredentialField("client_id", "Client ID"),
            CredentialField("client_secret", "Client Secret"),
        ),
        description="Company Page posting through LinkedIn Community Management API.",
    ),
    CredentialGroup(
        key="tiktok",
        title="TikTok",
        platforms=(PlatformCredential.Platform.TIKTOK,),
        fields=(
            CredentialField("client_key", "Client Key"),
            CredentialField("client_secret", "Client Secret"),
        ),
        description="Login Kit and Content Posting API for TikTok video publishing.",
        docs_hint="TikTok requires the redirect slug social1 instead of tiktok.",
    ),
    CredentialGroup(
        key="google",
        title="Google",
        platforms=(
            PlatformCredential.Platform.YOUTUBE,
            PlatformCredential.Platform.GOOGLE_BUSINESS,
        ),
        fields=(
            CredentialField("client_id", "OAuth Client ID"),
            CredentialField("client_secret", "OAuth Client Secret"),
        ),
        description="Shared Google OAuth client for YouTube and Google Business Profile.",
    ),
    CredentialGroup(
        key="pinterest",
        title="Pinterest",
        platforms=(PlatformCredential.Platform.PINTEREST,),
        fields=(
            CredentialField("app_id", "App ID"),
            CredentialField("app_secret", "App Secret"),
        ),
        description="Pinterest OAuth app for boards and pins.",
    ),
)

CREDENTIAL_GROUP_BY_KEY = {group.key: group for group in CREDENTIAL_GROUPS}

CREDENTIAL_FREE_PLATFORMS = (
    {
        "name": "Bluesky",
        "description": "Users connect with their handle and a Bluesky App Password.",
    },
    {
        "name": "Mastodon",
        "description": "Studio registers an OAuth app per Mastodon instance during connection.",
    },
)


@login_required
@require_org_role(OrgMembership.OrgRole.ADMIN)
@require_http_methods(["GET", "POST"])
def credentials_list(request):
    if request.org is None:
        raise PermissionDenied("Organization required.")

    if request.method == "POST":
        group = CREDENTIAL_GROUP_BY_KEY.get(request.POST.get("group", ""))
        if group is None:
            messages.error(request, "Unknown credential group.")
            return redirect("credentials:list")

        action = request.POST.get("action")
        if action == "save":
            _save_group(request, group)
        elif action == "clear":
            _clear_group(request, group)
        else:
            messages.error(request, "Unknown action.")
        return redirect("credentials:list")

    context = {
        "settings_active": "platform_credentials",
        "credential_groups": [_group_context(request.org, group) for group in CREDENTIAL_GROUPS],
        "credential_free_platforms": CREDENTIAL_FREE_PLATFORMS,
        "app_url": _app_url(),
    }
    return render(request, "credentials/list.html", context)


def _save_group(request, group: CredentialGroup) -> None:
    existing = _stored_or_env_credentials(request.org, group)
    credentials = {}
    missing = []

    for field in group.fields:
        raw_value = request.POST.get(f"field_{field.name}", "").strip()
        value = raw_value or existing.get(field.name, "")
        if not value:
            missing.append(field.label)
        credentials[field.name] = value

    if missing:
        messages.error(
            request,
            f"{group.title} is missing: {', '.join(missing)}. "
            "Existing configured values can be left blank, but new credentials require every field.",
        )
        return

    for platform in group.platforms:
        PlatformCredential.objects.update_or_create(
            organization=request.org,
            platform=platform,
            defaults={
                "credentials": credentials,
                "is_configured": True,
                "test_result": PlatformCredential.TestResult.UNTESTED,
                "tested_at": None,
            },
        )

    messages.success(request, f"{group.title} credentials saved.")


def _clear_group(request, group: CredentialGroup) -> None:
    PlatformCredential.objects.filter(
        organization=request.org,
        platform__in=group.platforms,
    ).update(
        credentials={},
        is_configured=False,
        test_result=PlatformCredential.TestResult.UNTESTED,
        tested_at=None,
    )
    if _env_configured_platforms(group):
        messages.warning(
            request,
            f"Saved {group.title} credentials cleared, but environment variables are still configured.",
        )
    else:
        messages.success(request, f"{group.title} credentials cleared.")


def _group_context(org, group: CredentialGroup) -> dict:
    configured_platforms = _configured_platforms(org, group)
    status = _status_for_group(group, configured_platforms)
    stored_or_env = _stored_or_env_credentials(org, group)
    return {
        "key": group.key,
        "title": group.title,
        "description": group.description,
        "docs_hint": group.docs_hint,
        "platforms": [_platform_label(platform) for platform in group.platforms],
        "status": status,
        "configured_platform_count": len(configured_platforms),
        "platform_count": len(group.platforms),
        "fields": [
            {
                "name": field.name,
                "label": field.label,
                "masked": _mask_secret(stored_or_env.get(field.name, "")),
                "type": "password" if field.secret else "text",
            }
            for field in group.fields
        ],
        "redirect_uris": [_redirect_uri(platform) for platform in group.platforms],
    }


def _configured_platforms(org, group: CredentialGroup) -> set[str]:
    configured = set(_env_configured_platforms(group))
    rows = PlatformCredential.objects.filter(organization=org, platform__in=group.platforms)
    for row in rows:
        if row.is_configured and _has_required_fields(row.credentials, group):
            configured.add(row.platform)
    return configured


def _env_configured_platforms(group: CredentialGroup) -> set[str]:
    env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
    return {platform for platform in group.platforms if _has_required_fields(env_creds.get(platform, {}), group)}


def _stored_or_env_credentials(org, group: CredentialGroup) -> dict:
    row = (
        PlatformCredential.objects.filter(
            organization=org,
            platform__in=group.platforms,
            is_configured=True,
        )
        .order_by("platform")
        .first()
    )
    if row and row.credentials:
        return dict(row.credentials)

    env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
    for platform in group.platforms:
        creds = env_creds.get(platform, {})
        if _has_required_fields(creds, group):
            return dict(creds)
    return {}


def _has_required_fields(credentials: dict | None, group: CredentialGroup) -> bool:
    credentials = credentials or {}
    return all(bool(credentials.get(name)) for name in group.field_names)


def _status_for_group(group: CredentialGroup, configured_platforms: set[str]) -> dict:
    if len(configured_platforms) == len(group.platforms):
        return {"key": "configured", "label": "Configured"}
    if configured_platforms:
        return {"key": "partial", "label": "Partially configured"}
    return {"key": "missing", "label": "Not configured"}


def _platform_label(platform: str) -> str:
    return dict(PlatformCredential.Platform.choices).get(platform, platform)


def _redirect_uri(platform: str) -> str:
    return f"{_app_url()}/social-accounts/callback/{to_url_slug(platform)}/"


def _app_url() -> str:
    return str(getattr(settings, "APP_URL", "http://localhost:8000")).rstrip("/")


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]
