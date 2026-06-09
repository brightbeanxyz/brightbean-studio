import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 3600  # hourly


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    verbose_name = "Analytics"

    def ready(self):
        from django.db.models.signals import post_migrate

        from . import signals  # noqa: F401

        # Register the recurring sync task with django-background-tasks. We
        # use ``post_migrate`` so the task table exists before we touch it;
        # mirrors the pattern in apps/publisher/apps.py.
        post_migrate.connect(self._register_sync_task, sender=self)

    @staticmethod
    def _register_sync_task(sender, **kwargs):
        """Idempotently register the hourly analytics sync cron."""
        try:
            from background_task.models import Task

            from apps.analytics.tasks import sync_all_account_analytics

            if not Task.objects.filter(verbose_name="sync_all_account_analytics").exists():
                sync_all_account_analytics(
                    repeat=SYNC_INTERVAL_SECONDS,
                    verbose_name="sync_all_account_analytics",
                )
                logger.info(
                    "Registered recurring analytics sync (every %ss)",
                    SYNC_INTERVAL_SECONDS,
                )
        except Exception:
            logger.debug("Skipping analytics sync registration (database not ready)")
