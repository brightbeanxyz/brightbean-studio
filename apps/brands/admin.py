from django.contrib import admin

from .models import BrandProfile, EditorialStrategy, EditorialStrategyVersion


@admin.register(BrandProfile)
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "industry", "primary_language", "is_active", "updated_at")
    list_filter = ("is_active", "primary_language", "industry")
    search_fields = ("name", "description", "industry", "workspace__name", "workspace__organization__name")
    list_select_related = ("workspace", "workspace__organization")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EditorialStrategy)
class EditorialStrategyAdmin(admin.ModelAdmin):
    list_display = ("brand", "reach_percentage", "authority_percentage", "conversion_percentage", "updated_at")
    search_fields = ("brand__name", "brand__workspace__name")
    list_select_related = ("brand", "brand__workspace")


@admin.register(EditorialStrategyVersion)
class EditorialStrategyVersionAdmin(admin.ModelAdmin):
    list_display = (
        "strategy",
        "version",
        "reach_percentage",
        "authority_percentage",
        "conversion_percentage",
        "created_at",
    )
    list_select_related = ("strategy", "strategy__brand")
    readonly_fields = (
        "strategy",
        "version",
        "reach_percentage",
        "authority_percentage",
        "conversion_percentage",
        "created_by",
        "created_at",
    )
