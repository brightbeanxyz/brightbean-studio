#!/usr/bin/env python3
"""Connect social accounts to BrightBean from stored credentials.

Wires Bluesky (handle + app password) and Mastodon (instance + user token)
into the BrightBean production workspace, replicating the web connect flows
(apps/social_accounts/views.py) for headless use.

Reads credentials from environment (set them as Fly secrets or pass inline):
  BLUESKY_HANDLE, BLUESKY_APP_PASSWORD
  MASTODON_INSTANCE_URL, MASTODON_ACCESS_TOKEN

Usage (production):
  fly ssh console --app brightbean-pnc -C "python scripts/connect_social_accounts.py"

Does NOT post anything. Connecting only; publishing stays behind the Eric gate.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from django.utils import timezone  # noqa: E402
from apps.social_accounts.models import SocialAccount  # noqa: E402
from apps.workspaces.models import Workspace  # noqa: E402
from apps.calendar.services import create_default_queue_and_slots  # noqa: E402
from apps.credentials.models import PlatformCredential  # noqa: E402
from providers.bluesky import BlueskyProvider  # noqa: E402


def _get_workspace():
    ws = Workspace.objects.order_by("created_at").first()
    if ws is None:
        raise RuntimeError("No workspace found in this BrightBean instance")
    return ws


def _upsert(workspace, platform, *, platform_id, name, handle, avatar, followers,
            access_token, refresh_token="", instance_url=""):
    account, created = SocialAccount.objects.update_or_create(
        workspace_id=workspace.id,
        platform=platform,
        account_platform_id=platform_id,
        defaults={
            "account_name": name,
            "account_handle": handle or "",
            "avatar_url": avatar or "",
            "follower_count": followers or 0,
            "oauth_access_token": access_token,
            "oauth_refresh_token": refresh_token or "",
            "instance_url": instance_url or "",
            "connection_status": SocialAccount.ConnectionStatus.CONNECTED,
            "last_error": "",
            "analytics_needs_reconnect": False,
        },
    )
    if created:
        create_default_queue_and_slots(account)
    return account, created


def connect_bluesky(workspace):
    handle = os.environ.get("BLUESKY_HANDLE", "").lstrip("@")
    app_password = os.environ.get("BLUESKY_APP_PASSWORD", "")
    if not handle or not app_password:
        print("Bluesky: SKIP (BLUESKY_HANDLE / BLUESKY_APP_PASSWORD not set)")
        return
    provider = BlueskyProvider()
    tokens = provider.create_session(handle, app_password)
    profile = provider.get_profile(tokens.access_token)
    account, created = _upsert(
        workspace, PlatformCredential.Platform.BLUESKY,
        platform_id=profile.platform_id, name=profile.name, handle=profile.handle,
        avatar=profile.avatar_url, followers=profile.follower_count,
        access_token=tokens.access_token, refresh_token=tokens.refresh_token,
        instance_url=provider.pds_url,
    )
    print(f"Bluesky: {'created' if created else 'updated'} -> {profile.handle}")


def connect_mastodon(workspace):
    import requests

    instance = os.environ.get("MASTODON_INSTANCE_URL", "").rstrip("/")
    token = os.environ.get("MASTODON_ACCESS_TOKEN", "")
    if not instance or not token:
        print("Mastodon: SKIP (MASTODON_INSTANCE_URL / MASTODON_ACCESS_TOKEN not set)")
        return
    resp = requests.get(
        f"{instance}/api/v1/accounts/verify_credentials",
        headers={"Authorization": f"Bearer {token}"}, timeout=20,
    )
    if resp.status_code != 200:
        print(f"Mastodon: token check failed ({resp.status_code}): {resp.text[:200]}")
        print("Mastodon: if 403 'confirmed e-mail', click the confirmation link in the inbox first")
        return
    me = resp.json()
    account, created = _upsert(
        workspace, PlatformCredential.Platform.MASTODON,
        platform_id=str(me["id"]), name=me.get("display_name") or me.get("acct", ""),
        handle=me.get("acct", ""), avatar=me.get("avatar", ""),
        followers=me.get("followers_count", 0),
        access_token=token, instance_url=instance,
    )
    print(f"Mastodon: {'created' if created else 'updated'} -> {me.get('acct')}")


def main():
    workspace = _get_workspace()
    print(f"Workspace: {workspace.name} ({workspace.id})")
    connect_bluesky(workspace)
    connect_mastodon(workspace)
    total = SocialAccount.objects.filter(workspace=workspace).count()
    print(f"Connected social accounts in workspace: {total}")


if __name__ == "__main__":
    main()
