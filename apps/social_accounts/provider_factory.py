"""Build a configured provider for a platform.

Lives apart from ``views`` so the webhook service layer can instantiate
providers without importing the view module back — ``views`` imports
``webhooks``, so the reverse edge would be a cycle.
"""

from apps.credentials.models import resolve_platform_credentials


def _get_provider_for_platform(platform: str, org_id, **extra_credentials):
    """Resolve app credentials and instantiate the provider."""
    from providers import get_provider

    # .env is dominant; admin-entered org credentials are the fallback.
    credentials = resolve_platform_credentials(platform, org_id)

    if extra_credentials:
        credentials = {**credentials, **extra_credentials}

    return get_provider(platform, credentials)
