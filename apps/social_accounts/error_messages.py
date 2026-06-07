"""User-facing error messages for social account health checks."""

from providers.exceptions import (
    APIError,
    OAuthError,
    RateLimitError,
    TokenExpiredError,
)

RECONNECT_MESSAGE = "Account connection expired. Please reconnect."
RATE_LIMIT_MESSAGE = "Rate limit reached. We'll retry this check shortly."
PLATFORM_UNAVAILABLE_MESSAGE = "The platform is temporarily unavailable. We'll retry shortly."
GENERIC_MESSAGE = "Connection check failed. Please try reconnecting."

_EXPIRED_TOKEN_ERRORS = {
    "ExpiredToken",
    "invalid_token",
    "InvalidToken",
    "invalid_grant",
}


def friendly_health_check_error(exc: Exception) -> str:
    """Map a provider exception to a short, user-facing message."""
    if isinstance(exc, TokenExpiredError):
        return RECONNECT_MESSAGE

    if isinstance(exc, RateLimitError):
        return RATE_LIMIT_MESSAGE

    if isinstance(exc, APIError):
        if exc.status_code in (401, 403):
            return RECONNECT_MESSAGE
        raw_error = (exc.raw_response or {}).get("error")
        if isinstance(raw_error, dict):
            error_code = raw_error.get("code") or raw_error.get("error_subcode") or raw_error.get("type")
        else:
            error_code = raw_error
        if error_code in _EXPIRED_TOKEN_ERRORS:
            return RECONNECT_MESSAGE
        if exc.status_code is not None and exc.status_code >= 500:
            return PLATFORM_UNAVAILABLE_MESSAGE
        return GENERIC_MESSAGE

    if isinstance(exc, OAuthError):
        return RECONNECT_MESSAGE

    return GENERIC_MESSAGE
