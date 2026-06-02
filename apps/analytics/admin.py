from django.contrib import admin

from .models import AccountInsightsSnapshot, PostInsightsSnapshot


@admin.register(AccountInsightsSnapshot)
class AccountInsightsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("social_account", "metric_key", "date", "value", "captured_at")
    list_filter = ("metric_key", "date")
    search_fields = ("social_account__account_name",)
    readonly_fields = ("captured_at",)


@admin.register(PostInsightsSnapshot)
class PostInsightsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("platform_post", "metric_key", "date", "value", "captured_at")
    list_filter = ("metric_key", "date")
    readonly_fields = ("captured_at",)
