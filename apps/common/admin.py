from django.contrib import admin

from .models import EmailSendCounter, EmailSuppression


@admin.register(EmailSendCounter)
class EmailSendCounterAdmin(admin.ModelAdmin):
    list_display = ("scope", "key", "period_start", "count")
    list_filter = ("scope", "period_start")
    search_fields = ("key",)
    readonly_fields = ("scope", "key", "period_start", "count")

    def has_add_permission(self, request):
        # Counters are written by the send path only; adding one by hand would
        # silently hand out or withdraw budget.
        return False


@admin.register(EmailSuppression)
class EmailSuppressionAdmin(admin.ModelAdmin):
    list_display = ("address", "reason", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("address", "detail")
    readonly_fields = ("created_at",)
