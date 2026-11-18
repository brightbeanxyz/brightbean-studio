"""No models.

This module exists so Django sends ``post_migrate`` for this app, which
``AboutConfig`` uses to keep the ``django.contrib.sites`` record in step with
``SITE_NAME`` and ``APP_URL``.
"""
