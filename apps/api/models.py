"""Persistence for cross-request invariants of the Agent API.

Right now this is just ``IdempotencyRecord``. Audit log lives in
``apps.api_keys.models.ApiKeyAuditLog`` (already created in Phase 1) since
it's keyed by API key, not by request.
"""

from __future__ import annotations

import uuid

from django.db import models


class IdempotencyRecord(models.Model):
    """Server-side cache of a POST response so retries are safe.

    Agents retry on network errors. Without idempotency, a retried
    ``POST /posts`` would double-create the Post + PlatformPost rows and
    eventually double-publish. Agents that want safe retries pass an
    ``Idempotency-Key`` header (or ``idempotency_key`` field); we cache
    the first response under ``(api_key, key)`` and replay it verbatim on
    subsequent matching requests for 24 hours.

    Fingerprint defends against the classic ID-reuse mistake — if the
    agent reuses the same key for a different request body, we return
    422 rather than silently replaying a stale response from a different
    intent.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api_key = models.ForeignKey(
        "api_keys.ApiKey",
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    key = models.CharField(
        max_length=128,
        help_text="Client-chosen idempotency key (free-form string, max 128 chars).",
    )
    request_fingerprint = models.CharField(
        max_length=64,
        help_text="SHA-256 of (method + path + canonical body); guards against key reuse with a different body.",
    )
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "agent_api_idempotency"
        unique_together = [("api_key", "key")]
        indexes = [
            models.Index(fields=["created_at"], name="idx_idem_created_at"),
        ]

    def __str__(self):
        return f"Idem({self.api_key_id}/{self.key}) -> {self.response_status}"
