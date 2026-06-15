import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MediaLibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.media_library"
    verbose_name = "Media Library"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(self._register_pending_upload_sweep, sender=self)

    @staticmethod
    def _register_pending_upload_sweep(sender, **kwargs):
        """Register the recurring presigned-upload sweep after migrations.

        Mirrors ``apps.api.apps``: re-registered idempotently on every migrate.
        Without this, expired-but-never-finalized ``PendingUpload`` rows and
        their partially-uploaded objects accumulate forever.
        """
        try:
            from background_task.models import Task

            from apps.media_library.tasks import (
                PENDING_UPLOAD_SWEEP_INTERVAL_SECONDS,
                sweep_pending_uploads,
            )

            if not Task.objects.filter(verbose_name="sweep_pending_uploads").exists():
                sweep_pending_uploads(
                    repeat=PENDING_UPLOAD_SWEEP_INTERVAL_SECONDS,
                    verbose_name="sweep_pending_uploads",
                )
                logger.info("Registered pending-upload sweep (every %ds)", PENDING_UPLOAD_SWEEP_INTERVAL_SECONDS)
        except Exception:
            # post_migrate can fire before the background-task tables exist on a
            # fresh DB; skip quietly so first-run setup doesn't error.
            logger.debug("Skipping pending-upload sweep registration (DB not ready)")
