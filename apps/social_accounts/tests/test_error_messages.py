"""Tests for the user-facing provider error translators."""

from datetime import UTC, datetime, timedelta

from apps.social_accounts.error_messages import (
    FIRST_COMMENT_GENERIC_MESSAGE,
    FIRST_COMMENT_QUOTA_EXHAUSTED_MESSAGE,
    FIRST_COMMENT_RECONNECT_MESSAGE,
    FIRST_COMMENT_REJECTED_MESSAGE,
    FIRST_COMMENT_TEMPORARY_MESSAGE,
    GENERIC_MESSAGE,
    PLATFORM_UNAVAILABLE_MESSAGE,
    PUBLISH_GENERIC_MESSAGE,
    PUBLISH_RECONNECT_MESSAGE,
    PUBLISH_REJECTED_MESSAGE,
    QUOTA_EXHAUSTED_MESSAGE,
    RATE_LIMIT_MESSAGE,
    RECONNECT_MESSAGE,
    friendly_first_comment_error,
    friendly_health_check_error,
    friendly_publish_error,
    quota_blocked_message,
    quota_connect_error,
)
from providers.exceptions import (
    APIError,
    OAuthError,
    PublishError,
    QuotaExceededError,
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


class TestQuotaAndTokenClassification:
    """Cover for the bug that had us telling healthy accounts to reconnect.

    Google answers a spent daily quota with 403. Before the provider layer told
    quota 403s apart from permission 403s, every one of them reached
    ``_classify`` as a plain ``APIError(403)`` → "reconnect", so an exhausted
    budget stamped "Account connection expired" on every YouTube account. Users
    reconnected, minted a fresh token, and the sync resumed burning quota.
    """

    def test_quota_exceeded_never_reads_as_reconnect(self):
        """The property this class exists for, whatever the copy says."""
        exc = QuotaExceededError("YouTube daily quota exhausted (data API)", status_code=403)

        assert friendly_health_check_error(exc) != RECONNECT_MESSAGE
        assert friendly_health_check_error(exc).startswith(QUOTA_EXHAUSTED_MESSAGE)

    def test_quota_exceeded_does_not_borrow_the_rate_limit_copy(self):
        """A daily budget is not a per-second throttle, and must not promise "shortly".

        ``QuotaExceededError`` subclasses ``RateLimitError``, so it used to
        inherit "We'll retry this check shortly" — which, for a window that
        refills at midnight US/Pacific, can be twenty hours from true.
        """
        exc = QuotaExceededError("spent", status_code=403)

        assert friendly_health_check_error(exc) != RATE_LIMIT_MESSAGE
        assert "shortly" not in friendly_health_check_error(exc)

    def test_a_known_reset_time_is_named(self):
        resets_at = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=9)
        exc = QuotaExceededError("spent", status_code=403, resets_at=resets_at)

        assert f"{resets_at:%H:%M} UTC" in friendly_health_check_error(exc)

    def test_an_unknown_reset_time_degrades_to_the_bare_sentence(self):
        """No ``resets_at`` must not produce a promise we cannot keep."""
        exc = QuotaExceededError("spent", status_code=403)

        assert friendly_health_check_error(exc) == QUOTA_EXHAUSTED_MESSAGE

    def test_quota_exceeded_is_its_own_case_for_a_first_comment(self):
        exc = QuotaExceededError("spent", status_code=403)

        assert friendly_first_comment_error(exc) == FIRST_COMMENT_QUOTA_EXHAUSTED_MESSAGE
        assert friendly_first_comment_error(exc) != FIRST_COMMENT_TEMPORARY_MESSAGE

    def test_the_connect_flow_never_says_try_again_with_no_wait(self):
        """ "Please try again" is the one thing that cannot work before the reset."""
        resets_at = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=5)
        exc = QuotaExceededError("spent", status_code=403, resets_at=resets_at, platform="YouTube")

        message = quota_connect_error(exc)

        assert message.startswith("YouTube's daily API limit is used up")
        assert f"Try again after {resets_at:%H:%M} UTC" in message

    def test_token_expired_carrying_a_status_still_reads_as_reconnect(self):
        """The class finally has a live raiser, and it now carries a status."""
        exc = TokenExpiredError("YouTube rejected the access token", status_code=401)

        assert friendly_health_check_error(exc) == RECONNECT_MESSAGE

    def test_a_genuine_permission_403_still_reads_as_reconnect(self):
        """Classification must not have moved the case it was never about."""
        exc = APIError("Forbidden", status_code=403)

        assert friendly_health_check_error(exc) == RECONNECT_MESSAGE


class TestThrottleIsNotASpentDay:
    """YouTube raises QuotaExceededError for a 5-minute throttle too.

    Mapping the class alone told users their daily limit was gone when a burst
    had merely been smoothed out — advice that is wrong in both directions,
    since one wants a moment's patience and the other wants until tomorrow.
    """

    def test_a_short_window_reads_as_a_rate_limit(self):
        exc = QuotaExceededError(
            "YouTube request rate throttled (data API)",
            status_code=403,
            resets_at=datetime.now(UTC) + timedelta(minutes=5),
        )

        assert friendly_health_check_error(exc) == RATE_LIMIT_MESSAGE

    def test_a_long_window_still_reads_as_exhausted(self):
        exc = QuotaExceededError(
            "YouTube daily quota exhausted (data API)",
            status_code=403,
            resets_at=datetime.now(UTC) + timedelta(hours=9),
        )

        assert friendly_health_check_error(exc).startswith(QUOTA_EXHAUSTED_MESSAGE)

    def test_no_window_at_all_stays_exhausted(self):
        """The class means a hard budget is spent; without an hour, say only that."""
        exc = QuotaExceededError("spent", status_code=403)

        assert friendly_health_check_error(exc) == QUOTA_EXHAUSTED_MESSAGE


class TestResetPhrase:
    def test_an_elapsed_deadline_never_names_an_hour_behind_the_user(self):
        """A window that has already rolled over is not a wait, and must not read as one.

        It classifies as short — zero remaining is less than the threshold — so
        the copy is the rate-limit one, which is exactly right: the block is
        over and the next attempt will go through. Either way the one
        unacceptable outcome is naming a time in the past, so assert that
        directly rather than just the branch.
        """
        resets_at = datetime.now(UTC) - timedelta(hours=2)
        exc = QuotaExceededError("spent", status_code=403, resets_at=resets_at)

        message = friendly_health_check_error(exc)

        assert message == RATE_LIMIT_MESSAGE
        assert f"{resets_at:%H:%M}" not in message

    def test_a_window_beyond_a_day_carries_the_date(self):
        resets_at = datetime.now(UTC) + timedelta(days=3)
        exc = QuotaExceededError("spent", status_code=403, resets_at=resets_at)

        assert f"{resets_at:%d %b %H:%M} UTC" in friendly_health_check_error(exc)

    def test_the_connect_verb_is_passed_not_patched(self):
        """The wording is a parameter, so rephrasing the shared helper cannot break it."""
        resets_at = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=5)
        exc = QuotaExceededError("spent", status_code=403, resets_at=resets_at, platform="YouTube")

        message = quota_connect_error(exc)

        assert f"Try again after {resets_at:%H:%M} UTC" in message
        assert "We'll resume" not in message

    def test_connect_short_throttle_does_not_claim_daily_quota_is_spent(self):
        resets_at = datetime.now(UTC) + timedelta(minutes=5)
        exc = QuotaExceededError("throttled", resets_at=resets_at, platform="YouTube")

        message = quota_connect_error(exc)

        assert "temporarily rate-limited" in message
        assert "daily API limit" not in message


class TestQuotaBlockedMessage:
    """What the card says while a recorded block is in force and nothing was called."""

    def test_it_names_the_platform_and_the_hour(self):
        blocked_until = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=6)

        message = quota_blocked_message("youtube", blocked_until)

        assert message.startswith("Youtube's daily API limit is used up")
        assert f"We'll resume after {blocked_until:%H:%M} UTC" in message

    def test_an_expired_block_names_no_hour(self):
        message = quota_blocked_message("youtube", datetime.now(UTC) - timedelta(hours=1))

        assert message == "Youtube's daily API limit is used up, so syncing is paused."

    def test_a_short_block_is_described_as_a_throttle(self):
        message = quota_blocked_message("youtube", datetime.now(UTC) + timedelta(minutes=5))

        assert "temporarily rate-limited" in message
        assert "daily API limit" not in message
