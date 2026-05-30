from django.apps import AppConfig


class ApiKeysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api_keys"
    verbose_name = "API Keys"

    def ready(self):
        # Wire signal handlers that bust the verify_token row cache when
        # admin-side edits change the key's scope. Without these, the
        # pickled prefetch cache (social_accounts) and the per-row
        # permissions / expires_at on the cached object survive for up
        # to REVOCATION_CACHE_TTL seconds after the admin save, letting
        # an agent operate against a scope the admin already revoked.
        from apps.api_keys import signals  # noqa: F401
