from django.contrib import admin

from apps.api_keys.models import ApiKey, ApiKeyAuditLog


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "issued_by", "lookup_prefix", "revoked_at", "last_used_at", "created_at")
    list_filter = ("workspace", "revoked_at")
    search_fields = ("name", "lookup_prefix")
    readonly_fields = (
        "id",
        "lookup_prefix",
        "token_hash",
        "last_used_at",
        "last_used_ip",
        "created_at",
    )
    filter_horizontal = ("social_accounts",)


@admin.register(ApiKeyAuditLog)
class ApiKeyAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "api_key", "action", "method", "path", "status_code", "ip")
    list_filter = ("action", "status_code")
    search_fields = ("path", "api_key__name")
    readonly_fields = tuple(f.name for f in ApiKeyAuditLog._meta.fields)
