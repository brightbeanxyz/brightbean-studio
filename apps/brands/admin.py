from django.contrib import admin

from .models import BrandProfile


@admin.register(BrandProfile)
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "industry", "primary_language", "is_active", "updated_at")
    list_filter = ("is_active", "primary_language", "industry")
    search_fields = ("name", "description", "industry", "workspace__name", "workspace__organization__name")
    list_select_related = ("workspace", "workspace__organization")
    readonly_fields = ("created_at", "updated_at")
