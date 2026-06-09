"""Unsplash integration plugin for BrightBean Studio.

Lives outside the main repo at ~/hermes-plugins/ so upstream merges
can't destroy it. Registers as a standard Django app.
"""

from django.apps import AppConfig


class BrightBeanUnsplashConfig(AppConfig):
    name = "apps.unsplash"
    verbose_name = "Unsplash Integration"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Signal wiring and other runtime setup goes here.
        # The context processor is registered via settings.TEMPLATES.
        pass
