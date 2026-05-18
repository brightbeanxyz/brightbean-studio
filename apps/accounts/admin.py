from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ApiToken, OAuthConnection, Session, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "name", "is_active", "is_staff", "created_at")
    list_filter = ("is_active", "is_staff", "totp_enabled")
    search_fields = ("email", "name")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name", "avatar")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("2FA", {"fields": ("totp_enabled",)}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(OAuthConnection)
class OAuthConnectionAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_email", "created_at")
    list_filter = ("provider",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_info", "ip_address", "last_active_at", "expires_at")
    list_filter = ("created_at",)


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "token_prefix", "scoped_workspace", "last_used_at", "created_at", "revoked_at")
    list_filter = ("created_at", "revoked_at")
    search_fields = ("user__email", "name", "token_prefix")
    readonly_fields = ("id", "token_prefix", "token_hash", "last_used_at", "created_at")
    fieldsets = (
        (None, {"fields": ("user", "name", "scoped_workspace")}),
        ("Token", {"fields": ("token_prefix", "token_hash")}),
        ("Lifecycle", {"fields": ("expires_at", "revoked_at", "last_used_at", "created_at")}),
    )
