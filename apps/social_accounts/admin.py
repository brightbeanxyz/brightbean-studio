from django.contrib import admin, messages

# Safe at module scope: signals.py imports no background_task at module level,
# and admin autodiscover runs after every app's models are loaded.
from apps.analytics.signals import BACKFILL_QUEUED_ATTR

from .models import AnalyticsPlatformConfig, MastodonAppRegistration, PlatformVisibility, SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = (
        "account_name",
        "platform",
        "workspace",
        "connection_status",
        "connected_at",
    )
    list_filter = ("platform", "connection_status")
    search_fields = ("account_name", "account_handle")
    readonly_fields = ("id", "created_at", "updated_at")
    exclude = ("oauth_access_token", "oauth_refresh_token")


@admin.register(MastodonAppRegistration)
class MastodonAppRegistrationAdmin(admin.ModelAdmin):
    list_display = ("instance_url", "created_at")
    readonly_fields = ("id", "created_at")
    exclude = ("client_id", "client_secret")


@admin.register(PlatformVisibility)
class PlatformVisibilityAdmin(admin.ModelAdmin):
    list_display = ("platform", "is_visible", "updated_at")
    list_editable = ("is_visible",)
    list_display_links = ("platform",)
    ordering = ("platform",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnalyticsPlatformConfig)
class AnalyticsPlatformConfigAdmin(admin.ModelAdmin):
    list_display = ("platform", "is_enabled", "updated_at")
    list_editable = ("is_enabled",)
    list_display_links = ("platform",)
    ordering = ("platform",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """Report the re-check that switching a platform on set in motion.

        The queueing itself lives in ``apps.analytics.signals`` so it also
        covers writes that never reach the admin (a shell ``save()``,
        ``update_or_create``). This only surfaces the count it recorded, so an
        operator ticking the box learns the save did something beyond flipping
        a flag. Nothing queued (already enabled, no connected accounts, or a
        platform with no analytics API) means nothing to report.
        """
        super().save_model(request, obj, form, change)
        queued = getattr(obj, BACKFILL_QUEUED_ATTR, 0)
        if queued:
            messages.info(
                request,
                f"Queued an analytics backfill for {queued} connected "
                f"{obj.get_platform_display()} account(s). Any whose connection predates this "
                f"may need reconnecting before insights can be read.",
            )
