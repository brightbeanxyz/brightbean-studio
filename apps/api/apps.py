import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    label = "agent_api"
    verbose_name = "Agent API"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(self._register_idempotency_sweep, sender=self)

    @staticmethod
    def _register_idempotency_sweep(sender, **kwargs):
        """Register the recurring stale-idempotency sweep after migrations.

        Mirrors the pattern in ``apps.publisher.apps`` so the sweep is
        re-registered idempotently on every migrate. Without this, the
        24h replay window the model docstring promises would not be
        enforced and PENDING placeholders left by crashed workers would
        accumulate forever.
        """
        try:
            from background_task.models import Task

            from apps.api.tasks import (
                SWEEP_INTERVAL_SECONDS,
                sweep_stale_idempotency_records,
            )

            if not Task.objects.filter(verbose_name="sweep_idempotency").exists():
                sweep_stale_idempotency_records(
                    repeat=SWEEP_INTERVAL_SECONDS,
                    verbose_name="sweep_idempotency",
                )
                logger.info("Registered idempotency sweep (every %ds)", SWEEP_INTERVAL_SECONDS)
        except Exception:
            # ``post_migrate`` fires before the background-task tables
            # might exist on a fresh DB; skip quietly so first-run setup
            # doesn't error.
            logger.debug("Skipping idempotency sweep registration (DB not ready)")
