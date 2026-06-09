"""Backfill ``view_analytics`` on existing full-scope API keys.

Until this PR, ``view_analytics`` was registered in
``apps/members/models.PERMISSION_KEYS`` but hidden from the issuance UI
via ``_HIDDEN_FROM_ISSUANCE`` (the agent-API analytics surface hadn't
shipped yet). Now that ``/api/v1/analytics/*`` and the two
``get_*_analytics`` MCP tools enforce the permission, keys issued
before the change cannot reach them — including keys whose operator
explicitly chose "all permissions" at issuance time.

This migration adds ``view_analytics`` to existing keys ONLY when their
stored ``permissions`` list already contains every other permission in
the catalog at the time the new gate landed. That preserves the
operator's intent ("this key is full-scope") without granting a new
capability to keys that were intentionally scoped down.

Keys with a partial permission set are left untouched: adding a new
capability to them would be an unjustified privilege escalation.
"""

from __future__ import annotations

from django.db import migrations

# The set of workspace permissions every "full-scope" key was issued with
# BEFORE ``view_analytics`` became grantable. Hardcoded here (not imported
# from ``apps.members.models.PERMISSION_KEYS``) so a future addition to
# the catalog can't retroactively shrink the migration's notion of
# "full scope" and skip backfilling keys that were full-scope when this
# migration was authored.
_PRE_ANALYTICS_FULL_SCOPE: frozenset[str] = frozenset(
    {
        "create_posts",
        "edit_others_posts",
        "approve_posts",
        "publish_directly",
        "manage_social_accounts",
        "use_inbox",
        "reply_from_inbox",
        "manage_workspace_settings",
        "upload_media",
        "edit_media",
        "delete_media",
        "manage_media",
    }
)


def add_view_analytics_to_full_scope_keys(apps, schema_editor):
    ApiKey = apps.get_model("api_keys", "ApiKey")
    to_update = []
    for key in ApiKey.objects.all():
        perms = set(key.permissions or [])
        if "view_analytics" in perms:
            continue
        # Only backfill keys that already hold every non-analytics
        # permission — these are full-scope keys whose operator's intent
        # was "grant everything". Partial-scope keys remain untouched.
        if perms >= _PRE_ANALYTICS_FULL_SCOPE:
            key.permissions = sorted(perms | {"view_analytics"})
            to_update.append(key)
    if to_update:
        ApiKey.objects.bulk_update(to_update, ["permissions"])


def remove_view_analytics_from_backfilled_keys(apps, schema_editor):
    """Reverse: best-effort removal for rollback.

    We can't perfectly identify which keys were backfilled vs. which were
    issued with ``view_analytics`` explicitly after the change, so the
    reverse drops the permission from any key whose post-removal set
    matches the pre-analytics full-scope catalog exactly. Keys with a
    partial set (where ``view_analytics`` was always explicit) are left
    alone.
    """
    ApiKey = apps.get_model("api_keys", "ApiKey")
    to_update = []
    for key in ApiKey.objects.all():
        perms = set(key.permissions or [])
        if "view_analytics" not in perms:
            continue
        if (perms - {"view_analytics"}) == _PRE_ANALYTICS_FULL_SCOPE:
            key.permissions = sorted(perms - {"view_analytics"})
            to_update.append(key)
    if to_update:
        ApiKey.objects.bulk_update(to_update, ["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("api_keys", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            add_view_analytics_to_full_scope_keys,
            reverse_code=remove_view_analytics_from_backfilled_keys,
        ),
    ]
