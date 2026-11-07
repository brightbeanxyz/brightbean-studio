from django.contrib import admin

from .models import ContentPlan, ContentPlanItem


class ContentPlanItemInline(admin.TabularInline):
    model = ContentPlanItem
    extra = 0
    readonly_fields = ("position", "planned_for", "objective", "topic", "recommended_platform")


@admin.register(ContentPlan)
class ContentPlanAdmin(admin.ModelAdmin):
    list_display = ("brand", "cadence", "start_date", "end_date", "status", "created_at")
    list_filter = ("cadence", "status")
    search_fields = ("brand__name", "workspace__name")
    list_select_related = ("brand", "workspace", "strategy_version")
    inlines = (ContentPlanItemInline,)


@admin.register(ContentPlanItem)
class ContentPlanItemAdmin(admin.ModelAdmin):
    list_display = ("plan", "position", "planned_for", "objective", "topic", "recommended_platform")
    list_filter = ("objective", "recommended_platform", "recommended_format")
    search_fields = ("topic", "hook", "content_pillar")
