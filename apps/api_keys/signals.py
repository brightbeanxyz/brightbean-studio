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

import contextlib

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.api_keys.models import ApiKey
from apps.api_keys.services import invalidate_api_key_cache

#: Stash key for the pre-clear snapshot. We attach it to the SocialAccount
#: instance because Django re-uses the same Python object across
#: ``pre_clear`` and ``post_clear`` for a single ``.clear()`` call.
_PRE_CLEAR_SNAPSHOT_ATTR = "_apikeys_pre_clear_snapshot"


@receiver(m2m_changed, sender=ApiKey.social_accounts.through)
def _invalidate_on_social_accounts_change(sender, instance, action, pk_set, **_):
    """Bust the cached row for every ApiKey whose allowlist just changed.

    Django fires this signal for ``add``, ``remove``, ``clear`` and their
    reverse-direction equivalents. The handler has to be careful about
    the reverse remove/clear paths:

    * **Forward direction** (``instance`` is the ``ApiKey``) — just bust
      that one row. ``pk_set`` is the set of ``SocialAccount`` IDs
      being touched, which we don't need.
    * **Reverse direction** (``instance`` is the ``SocialAccount``):
      - ``post_add`` — ``pk_set`` is the ``ApiKey`` IDs being added.
        We can also query ``instance.api_keys`` after the fact since
        ``add`` is additive. Either works.
      - ``post_remove`` — Codex (PR #53) flagged: by the time this
        fires, the relation is gone, so
        ``ApiKey.objects.filter(social_accounts=instance)`` MISSES
        the keys that just lost the relation. We must read from
        ``pk_set`` instead.
      - ``post_clear`` — same problem, plus ``pk_set`` is ``None``
        for clear. We capture the affected IDs in ``pre_clear``
        below and replay them in ``post_clear``.
    """
    if isinstance(instance, ApiKey):
        if action in {"post_add", "post_remove", "post_clear"}:
            invalidate_api_key_cache(instance)
        return

    # Reverse direction below — instance is a SocialAccount.
    if action == "post_add" or action == "post_remove":
        # pk_set is the set of ApiKey IDs being added/removed. After
        # ``post_remove`` the M2M no longer contains them, so we MUST
        # use pk_set rather than a fresh query.
        if not pk_set:
            return
        for ak in ApiKey.objects.filter(pk__in=pk_set).only("lookup_prefix"):
            invalidate_api_key_cache(ak)
        return

    if action == "pre_clear":
        # Snapshot every ApiKey ID currently related so we can invalidate
        # them in ``post_clear`` (after the clear, the relation is gone
        # and there's no way to recover them).
        ids = list(instance.api_keys.values_list("pk", flat=True))
        setattr(instance, _PRE_CLEAR_SNAPSHOT_ATTR, ids)
        return

    if action == "post_clear":
        ids = getattr(instance, _PRE_CLEAR_SNAPSHOT_ATTR, [])
        with contextlib.suppress(AttributeError):
            delattr(instance, _PRE_CLEAR_SNAPSHOT_ATTR)
        if not ids:
            return
        for ak in ApiKey.objects.filter(pk__in=ids).only("lookup_prefix"):
            invalidate_api_key_cache(ak)
        return


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
