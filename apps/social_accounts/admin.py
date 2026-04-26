from django.contrib import admin

from .models import MastodonAppRegistration, PlatformVisibility, SocialAccount


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
