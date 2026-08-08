"""Tests for the user-facing provider error translators."""

from apps.social_accounts.error_messages import (
    FIRST_COMMENT_GENERIC_MESSAGE,
    FIRST_COMMENT_RECONNECT_MESSAGE,
    FIRST_COMMENT_REJECTED_MESSAGE,
    FIRST_COMMENT_TEMPORARY_MESSAGE,
    GENERIC_MESSAGE,
    PLATFORM_UNAVAILABLE_MESSAGE,
    PUBLISH_GENERIC_MESSAGE,
    PUBLISH_RECONNECT_MESSAGE,
    PUBLISH_REJECTED_MESSAGE,
    RATE_LIMIT_MESSAGE,
    RECONNECT_MESSAGE,
    friendly_first_comment_error,
    friendly_health_check_error,
    friendly_publish_error,
)
from providers.exceptions import (
    APIError,
    OAuthError,
    PublishError,
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


def test_a_meta_error_payload_does_not_crash_the_classifier():
    """``raw_response["error"]`` is a dict on every Graph error and a bare
    string only on OAuth token endpoints. Hashing the dict against the
    expired-token set raises TypeError, which escapes the caller's own except."""
    exc = APIError(
        "boom",
        status_code=400,
        raw_response={"error": {"code": 20, "type": "OAuthException", "error_subcode": 1772107}},
    )

    assert friendly_health_check_error(exc) == GENERIC_MESSAGE


def test_first_comment_reconnect_on_an_auth_rejection():
    assert friendly_first_comment_error(APIError("nope", status_code=401)) == FIRST_COMMENT_RECONNECT_MESSAGE
    assert friendly_first_comment_error(TokenExpiredError("gone")) == FIRST_COMMENT_RECONNECT_MESSAGE
    # TokenExpiredError text is not passed through: an auth failure maps to
    # better advice than whatever the provider happened to say.
    assert "gone" not in friendly_first_comment_error(TokenExpiredError("gone"))


def test_first_comment_temporary_on_a_rate_limit_or_server_error():
    assert friendly_first_comment_error(RateLimitError("slow")) == FIRST_COMMENT_TEMPORARY_MESSAGE
    assert friendly_first_comment_error(APIError("boom", status_code=502)) == FIRST_COMMENT_TEMPORARY_MESSAGE


def test_first_comment_rejected_drops_the_platform_response_body():
    exc = APIError(
        'Instagram API error 400: {"error":{"type":"OAuthException","fbtrace_id":"A4B_mFUQTXKx"}}',
        status_code=400,
    )

    message = friendly_first_comment_error(exc)

    assert message == FIRST_COMMENT_REJECTED_MESSAGE
    assert "fbtrace_id" not in message


def test_first_comment_keeps_a_message_we_wrote_ourselves():
    """PublishError is the one class whose message is always written by us for
    a human, so it is the one class that passes through."""
    exc = PublishError("Instagram container processing timed out")

    assert friendly_first_comment_error(exc) == "Instagram container processing timed out"


def test_first_comment_generic_for_a_non_provider_exception():
    assert friendly_first_comment_error(ValueError("boom")) == FIRST_COMMENT_GENERIC_MESSAGE


def test_publish_error_drops_the_platform_response_body():
    exc = APIError('TikTok API error 400: {"error":{"code":"spam_risk_too_many_posts"}}', status_code=400)

    message = friendly_publish_error(exc)

    assert message == PUBLISH_REJECTED_MESSAGE
    assert "spam_risk_too_many_posts" not in message


def test_publish_error_keeps_a_message_we_wrote_ourselves():
    """The TikTok audit and container-timeout messages tell a user exactly what
    happened; a blanket rewrite would throw that away."""
    exc = PublishError("TikTok rejected the post: audit pending", retryable=False)

    assert friendly_publish_error(exc) == "TikTok rejected the post: audit pending"


def test_publish_error_reconnect_on_an_auth_rejection():
    assert friendly_publish_error(APIError("nope", status_code=403)) == PUBLISH_RECONNECT_MESSAGE


def test_publish_error_generic_for_a_non_provider_exception():
    assert friendly_publish_error(RuntimeError("boom")) == PUBLISH_GENERIC_MESSAGE


def test_an_oauth_error_body_is_never_shown():
    """instagram_login interpolates the token-exchange body into OAuthError,
    and a reconnect prompt is better advice than that body anyway."""
    exc = OAuthError('Instagram token exchange failed: {"error_message":"Invalid platform app"}')

    assert friendly_publish_error(exc) == PUBLISH_RECONNECT_MESSAGE
    assert friendly_first_comment_error(exc) == FIRST_COMMENT_RECONNECT_MESSAGE


def test_a_publish_error_quoting_a_json_body_is_not_passed_through():
    """Providers are meant to put bodies in raw_response, but that is a
    convention a new provider can break silently."""
    exc = PublishError('Threads container creation failed: {"error":{"fbtrace_id":"A4B"}}')

    message = friendly_publish_error(exc)

    assert message == PUBLISH_GENERIC_MESSAGE
    assert "fbtrace_id" not in message


def test_a_publish_error_quoting_a_dict_repr_is_not_passed_through():
    exc = PublishError("DEV.to article creation returned no id: {'error': 'unauthorized', 'status': 401}")

    assert friendly_publish_error(exc) == PUBLISH_GENERIC_MESSAGE


def test_an_overlong_publish_error_is_not_passed_through():
    assert friendly_publish_error(PublishError("x" * 301)) == PUBLISH_GENERIC_MESSAGE
    assert friendly_publish_error(PublishError("x" * 300)) == "x" * 300
