"""Signal handlers that bust the ``verify_token`` row cache on admin edits.

Codex review (Phase 1) flagged that ``verify_token`` caches the full
``ApiKey`` row — including its prefetched ``social_accounts`` M2M and
the values of ``permissions`` and ``expires_at`` — for
``REVOCATION_CACHE_TTL`` (30 s). Without an invalidation hook, admin
edits via the Django admin take that long to propagate, and during the
window the agent keeps acting on the pre-edit scope. These handlers
collapse the propagation delay to "next request" for the common admin
operations: adding/removing allowlisted accounts and editing
permissions / expiry on an existing key.
"""

from __future__ import annotations

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.api_keys.models import ApiKey
from apps.api_keys.services import invalidate_api_key_cache


@receiver(m2m_changed, sender=ApiKey.social_accounts.through)
def _invalidate_on_social_accounts_change(sender, instance, action, **_):
    """Bust the cached row on every M2M mutation that changes the allowlist.

    Django fires this signal for ``add``, ``remove``, ``clear`` and their
    ``reverse``-direction equivalents. We bust on every *post_* action so
    the next ``verify_token`` call observes the new allowlist regardless
    of which direction the admin used.
    """
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    if isinstance(instance, ApiKey):
        invalidate_api_key_cache(instance)
    # Reverse direction: instance is a ``SocialAccount`` and pk_set
    # contains the related ``ApiKey`` ids. Bust every affected key.
    else:
        api_keys = ApiKey.objects.filter(social_accounts=instance).only("lookup_prefix")
        for ak in api_keys:
            invalidate_api_key_cache(ak)


@receiver(post_save, sender=ApiKey)
def _invalidate_on_apikey_save(sender, instance, created, **_):
    """Bust the cached row whenever an ``ApiKey`` row is saved.

    Covers the most common admin paths that affect what ``verify_token``
    returns: changing ``permissions`` (the per-request intersection
    pulls from the cached row), ``expires_at`` (affects ``is_active``),
    or any other scope-relevant column. Creation also busts to keep the
    invariant "any save propagates immediately" — newly issued keys
    can't have a pre-existing cache entry anyway, so this is a no-op
    fast path in that case.
    """
    invalidate_api_key_cache(instance)
