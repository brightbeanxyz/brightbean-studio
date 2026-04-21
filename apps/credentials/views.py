from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.members.models import OrgMembership

from .models import PlatformCredential

# Define what fields each platform needs, with help text and developer console URLs
PLATFORM_FIELDS = {
    "facebook": {
        "label": "Facebook",
        "fields": [
            {"name": "app_id", "label": "App ID", "type": "text"},
            {"name": "app_secret", "label": "App Secret", "type": "password"},
        ],
        "help": "Create an app at Meta for Developers. You'll need a Facebook App with Facebook Login enabled.",
        "docs_url": "https://developers.facebook.com/apps/",
        "docs_label": "Meta for Developers",
        "shared_with": ["Instagram", "Threads"],
    },
    "instagram": {
        "label": "Instagram (Business)",
        "fields": [
            {"name": "app_id", "label": "App ID", "type": "text"},
            {"name": "app_secret", "label": "App Secret", "type": "password"},
        ],
        "help": "Uses the same Meta App as Facebook. Enable Instagram Graph API in your app settings.",
        "docs_url": "https://developers.facebook.com/apps/",
        "docs_label": "Meta for Developers",
        "shared_with": ["Facebook", "Threads"],
    },
    "instagram_personal": {
        "label": "Instagram (Personal)",
        "fields": [
            {"name": "app_id", "label": "App ID", "type": "text"},
            {"name": "app_secret", "label": "App Secret", "type": "password"},
        ],
        "help": "Requires a separate Instagram App (not the Facebook App). Enable Instagram Basic Display API.",
        "docs_url": "https://developers.facebook.com/apps/",
        "docs_label": "Meta for Developers",
    },
    "threads": {
        "label": "Threads",
        "fields": [
            {"name": "app_id", "label": "App ID", "type": "text"},
            {"name": "app_secret", "label": "App Secret", "type": "password"},
        ],
        "help": "Uses the same Meta App as Facebook. Enable Threads API in your app settings.",
        "docs_url": "https://developers.facebook.com/apps/",
        "docs_label": "Meta for Developers",
        "shared_with": ["Facebook", "Instagram"],
    },
    "linkedin_personal": {
        "label": "LinkedIn (Personal)",
        "fields": [
            {"name": "client_id", "label": "Client ID", "type": "text"},
            {"name": "client_secret", "label": "Client Secret", "type": "password"},
        ],
        "help": "Create an app in the LinkedIn Developer Portal. Request the Community Management API product.",
        "docs_url": "https://www.linkedin.com/developers/apps",
        "docs_label": "LinkedIn Developer Portal",
        "shared_with": ["LinkedIn (Company)"],
    },
    "linkedin_company": {
        "label": "LinkedIn (Company)",
        "fields": [
            {"name": "client_id", "label": "Client ID", "type": "text"},
            {"name": "client_secret", "label": "Client Secret", "type": "password"},
        ],
        "help": "Uses the same LinkedIn app as Personal. Ensure Community Management API access is approved.",
        "docs_url": "https://www.linkedin.com/developers/apps",
        "docs_label": "LinkedIn Developer Portal",
        "shared_with": ["LinkedIn (Personal)"],
    },
    "tiktok": {
        "label": "TikTok",
        "fields": [
            {"name": "client_key", "label": "Client Key", "type": "text"},
            {"name": "client_secret", "label": "Client Secret", "type": "password"},
        ],
        "help": "Register at the TikTok for Developers portal. Create a Login Kit app and request content posting scope.",
        "docs_url": "https://developers.tiktok.com/",
        "docs_label": "TikTok for Developers",
    },
    "youtube": {
        "label": "YouTube",
        "fields": [
            {"name": "client_id", "label": "Client ID", "type": "text"},
            {"name": "client_secret", "label": "Client Secret", "type": "password"},
        ],
        "help": "Create OAuth credentials in Google Cloud Console. Enable the YouTube Data API v3.",
        "docs_url": "https://console.cloud.google.com/apis/credentials",
        "docs_label": "Google Cloud Console",
        "shared_with": ["Google Business Profile"],
    },
    "google_business": {
        "label": "Google Business Profile",
        "fields": [
            {"name": "client_id", "label": "Client ID", "type": "text"},
            {"name": "client_secret", "label": "Client Secret", "type": "password"},
        ],
        "help": "Uses the same Google OAuth client as YouTube. Enable the Google My Business API.",
        "docs_url": "https://console.cloud.google.com/apis/credentials",
        "docs_label": "Google Cloud Console",
        "shared_with": ["YouTube"],
    },
    "pinterest": {
        "label": "Pinterest",
        "fields": [
            {"name": "app_id", "label": "App ID", "type": "text"},
            {"name": "app_secret", "label": "App Secret", "type": "password"},
        ],
        "help": "Create an app at Pinterest for Developers. Request access to the Content Publishing API.",
        "docs_url": "https://developers.pinterest.com/apps/",
        "docs_label": "Pinterest for Developers",
    },
    "bluesky": {
        "label": "Bluesky",
        "fields": [],
        "help": "Bluesky uses app passwords instead of OAuth. No developer credentials needed — users connect directly with their handle and an app password.",
        "no_setup_needed": True,
    },
    "mastodon": {
        "label": "Mastodon",
        "fields": [
            {"name": "instance_url", "label": "Instance URL", "type": "text", "placeholder": "https://mastodon.social"},
            {"name": "client_id", "label": "Client ID", "type": "text"},
            {"name": "client_secret", "label": "Client Secret", "type": "password"},
        ],
        "help": "Register an application on your Mastodon instance under Preferences > Development > New Application.",
        "docs_url": "https://docs.joinmastodon.org/client/token/",
        "docs_label": "Mastodon Docs",
    },
}


@login_required
def credentials_list(request):
    """Show all platforms with their configuration status."""
    org = request.org
    if not org:
        return redirect("/")

    # Get existing credentials from DB
    existing = {
        c.platform: c for c in PlatformCredential.objects.filter(organization=org)
    }

    platforms = []
    for platform_value, config in PLATFORM_FIELDS.items():
        cred = existing.get(platform_value)
        platforms.append({
            "value": platform_value,
            "label": config["label"],
            "is_configured": cred.is_configured if cred else False,
            "test_result": cred.test_result if cred else "untested",
            "masked": cred.masked_credentials if cred else {},
            "config": config,
        })

    return render(request, "credentials/list.html", {
        "platforms": platforms,
        "settings_active": "credentials",
    })


@login_required
@require_POST
def credentials_save(request, platform):
    """Save platform credentials from the setup form."""
    org = request.org
    if not org:
        return JsonResponse({"error": "No organization"}, status=400)

    # Only owners/admins can manage credentials
    if request.org_membership.org_role not in (
        OrgMembership.OrgRole.OWNER,
        OrgMembership.OrgRole.ADMIN,
    ):
        return JsonResponse({"error": "Permission denied"}, status=403)

    config = PLATFORM_FIELDS.get(platform)
    if not config:
        return JsonResponse({"error": "Unknown platform"}, status=400)

    # Build credentials dict from POST data
    credentials = {}
    for field in config.get("fields", []):
        value = request.POST.get(field["name"], "").strip()
        if value:
            credentials[field["name"]] = value

    # Check if all required fields are provided
    has_all = all(
        request.POST.get(f["name"], "").strip()
        for f in config.get("fields", [])
    )

    cred, _created = PlatformCredential.objects.update_or_create(
        organization=org,
        platform=platform,
        defaults={
            "credentials": credentials,
            "is_configured": has_all and bool(credentials),
            "test_result": PlatformCredential.TestResult.UNTESTED,
        },
    )

    if has_all and credentials:
        messages.success(request, f"{config['label']} credentials saved successfully.")
    else:
        messages.warning(request, f"Some fields are missing for {config['label']}.")

    return redirect("credentials:list")


@login_required
@require_POST
def credentials_remove(request, platform):
    """Remove platform credentials."""
    org = request.org
    if not org:
        return JsonResponse({"error": "No organization"}, status=400)

    if request.org_membership.org_role not in (
        OrgMembership.OrgRole.OWNER,
        OrgMembership.OrgRole.ADMIN,
    ):
        return JsonResponse({"error": "Permission denied"}, status=403)

    PlatformCredential.objects.filter(organization=org, platform=platform).delete()
    messages.success(request, "Credentials removed.")
    return redirect("credentials:list")
