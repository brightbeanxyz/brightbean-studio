from urllib.parse import urlparse

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_site_record(sender, using="default", **kwargs):
    """Point the django.contrib.sites record at this studio after every migrate.

    BrightBean's accounts migration 0004 names the site "Brightbean" at
    studio.brightbean.xyz, and allauth puts ``Site.name`` into email subjects.
    Doing this on post_migrate rather than in a migration keeps it correct when
    SITE_NAME or APP_URL change on an existing install.
    """
    from django.conf import settings
    from django.contrib.sites.models import Site

    domain = urlparse(settings.APP_URL).netloc or "localhost"
    Site.objects.using(using).update_or_create(
        pk=settings.SITE_ID,
        defaults={"name": settings.SITE_NAME[:50], "domain": domain[:100]},
    )
    Site.objects.clear_cache()


class AboutConfig(AppConfig):
    """Studio identity, the AGPL source page, and production deploy checks."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.about"
    label = "about"
    verbose_name = "About this studio"

    def ready(self):
        from apps.about import checks  # noqa: F401  (registers the deploy checks)

        post_migrate.connect(sync_site_record, sender=self, dispatch_uid="about.sync_site_record")
