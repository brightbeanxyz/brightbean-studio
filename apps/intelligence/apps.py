import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class IntelligenceConfig(AppConfig):
    name = "apps.intelligence"
    label = "intelligence"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.conf import settings
        from django.db.models.signals import post_migrate

        # Only schedule background tasks when the integration is actually
        # enabled. A self-hoster who hasn't configured Intelligence env
        # vars shouldn't see periodic /internal/v1/ calls failing in
        # their logs.
        if not getattr(settings, "INTELLIGENCE_ENABLED", False):
            return

        post_migrate.connect(self._register_recurring_tasks, sender=self)

    @staticmethod
    def _register_recurring_tasks(sender, **kwargs):
        """Schedule recurring reconcile after migrations apply.

        Idempotent, only schedules if no row with our verbose_name
        already exists. ``django-background-tasks`` matches verbose_name
        for the dedup check.
        """
        try:
            from background_task.models import Task

            from apps.intelligence.tasks import reconcile_intelligence_subscriptions

            if not Task.objects.filter(
                verbose_name="intelligence_reconcile",
            ).exists():
                reconcile_intelligence_subscriptions(
                    repeat=6 * 3600,  # every 6 hours
                    verbose_name="intelligence_reconcile",
                )
                logger.info("Registered recurring intelligence reconcile task (every 6h)")
        except Exception:
            logger.debug("Skipping intelligence reconcile registration (DB not ready)")
