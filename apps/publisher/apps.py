from django.apps import AppConfig


class PublisherConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.publisher"
    verbose_name = "Publishing Engine"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(self._register_tasks, sender=self)

    @staticmethod
    def _register_tasks(sender, **kwargs):
        from apps.common.background import register_recurring_task
        from apps.publisher.tasks import (
            PUBLISH_CONFIRM_INTERVAL_SECONDS,
            PUBLISH_CYCLE_INTERVAL_SECONDS,
            confirm_pending_publishes,
            run_publish_cycle,
        )

        # Publish what's due (every 15s), then settle what's in flight (every
        # 60s) — confirming asynchronous publishes and failing rows whose worker
        # was killed mid-publish, which nothing else recovers.
        register_recurring_task(
            run_publish_cycle,
            repeat=PUBLISH_CYCLE_INTERVAL_SECONDS,
            verbose_name="run_publish_cycle",
        )
        register_recurring_task(
            confirm_pending_publishes,
            repeat=PUBLISH_CONFIRM_INTERVAL_SECONDS,
            verbose_name="confirm_pending_publishes",
        )
