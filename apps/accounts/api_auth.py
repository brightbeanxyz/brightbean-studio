"""API token generation and verification for the MCP server."""

import hashlib
import secrets

from django.utils import timezone

from .models import ApiToken, User

TOKEN_PREFIX = "bbn_"
TOKEN_BYTES = 30
PREFIX_LEN = 12


def generate_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(TOKEN_BYTES)}"


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_token(
    *,
    user: User,
    name: str,
    scoped_workspace=None,
    expires_at=None,
) -> tuple[ApiToken, str]:
    raw = generate_token()
    token = ApiToken.objects.create(
        user=user,
        name=name,
        token_prefix=raw[:PREFIX_LEN],
        token_hash=hash_token(raw),
        scoped_workspace=scoped_workspace,
        expires_at=expires_at,
    )
    return token, raw


def authenticate_token(raw: str | None) -> tuple[User, ApiToken] | None:
    if not raw or not raw.startswith(TOKEN_PREFIX):
        return None
    tok = (
        ApiToken.objects.select_related("user", "scoped_workspace")
        .filter(token_hash=hash_token(raw), revoked_at__isnull=True)
        .first()
    )
    if tok is None:
        return None
    if tok.expires_at is not None and tok.expires_at < timezone.now():
        return None
    ApiToken.objects.filter(pk=tok.pk).update(last_used_at=timezone.now())
    return tok.user, tok
