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


def apply_analytics_scope_flag(provider, platform: str) -> None:
    """Set ``provider.include_analytics_scopes`` from AnalyticsPlatformConfig.

    Providers add their analytics-only scopes (e.g. ``read_insights``) to the
    OAuth scope list only when this flag is True, so a self-hoster whose Meta or
    Google app has not been approved for them can still connect for publishing.

    Anything reasoning about *what we asked for* must apply this first — the
    unconditional ``required_scopes`` is not what OAuth requested.
    """
    from apps.social_accounts.models import AnalyticsPlatformConfig

    provider.include_analytics_scopes = platform in AnalyticsPlatformConfig.enabled_platforms()
