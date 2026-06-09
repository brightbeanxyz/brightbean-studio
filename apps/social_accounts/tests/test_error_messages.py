"""Tests for the health check error message translator."""

from apps.social_accounts.error_messages import (
    GENERIC_MESSAGE,
    PLATFORM_UNAVAILABLE_MESSAGE,
    RATE_LIMIT_MESSAGE,
    RECONNECT_MESSAGE,
    friendly_health_check_error,
)
from providers.exceptions import (
    APIError,
    OAuthError,
    RateLimitError,
    TokenExpiredError,
)


def test_token_expired_error_maps_to_reconnect():
    assert friendly_health_check_error(TokenExpiredError("expired")) == RECONNECT_MESSAGE


def test_oauth_error_maps_to_reconnect():
    assert friendly_health_check_error(OAuthError("nope")) == RECONNECT_MESSAGE


def test_rate_limit_error_maps_to_rate_limit_message():
    assert friendly_health_check_error(RateLimitError("slow down")) == RATE_LIMIT_MESSAGE


def test_api_error_401_maps_to_reconnect():
    exc = APIError("unauthorized", status_code=401)
    assert friendly_health_check_error(exc) == RECONNECT_MESSAGE


def test_api_error_403_maps_to_reconnect():
    exc = APIError("forbidden", status_code=403)
    assert friendly_health_check_error(exc) == RECONNECT_MESSAGE


def test_bluesky_expired_token_in_raw_response_maps_to_reconnect():
    exc = APIError(
        "Bluesky API error 400: ...",
        status_code=400,
        raw_response={"error": "ExpiredToken", "message": "Token has expired"},
    )
    assert friendly_health_check_error(exc) == RECONNECT_MESSAGE


def test_api_error_5xx_maps_to_platform_unavailable():
    exc = APIError("boom", status_code=503)
    assert friendly_health_check_error(exc) == PLATFORM_UNAVAILABLE_MESSAGE


def test_generic_api_error_maps_to_generic_message():
    exc = APIError("something", status_code=400)
    assert friendly_health_check_error(exc) == GENERIC_MESSAGE


def test_bare_exception_maps_to_generic_message():
    assert friendly_health_check_error(Exception("boom")) == GENERIC_MESSAGE
