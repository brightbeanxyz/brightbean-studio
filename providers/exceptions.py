"""Exception hierarchy for social platform providers."""

from datetime import UTC, datetime, timedelta

# Where a spent budget stops being a momentary throttle and becomes a lost day.
#
# :class:`QuotaExceededError` covers both, because both are the platform saying
# "not now" and both want the same circuit breaker. They want opposite things
# from everyone else: a 5-second throttle is worth a pause and no alarm, while
# an exhausted daily budget means the platform is gone until it refills — and
# the user needs telling, in words that name the hour rather than promising to
# retry "shortly".
#
# The threshold lives here, next to the ``resets_at`` it reads, because its two
# consumers sit in different apps (``apps.common.quota`` for how loudly to log,
# ``apps.social_accounts.error_messages`` for what to tell the user) and neither
# should have to import the other to agree on the answer.
LONG_QUOTA_WINDOW = timedelta(hours=1)


def is_long_window(resets_at: datetime | None, now: datetime | None = None) -> bool:
    """Whether a refusal lasting until ``resets_at`` is a lost day, not a pause.

    An unknown or unreadable deadline counts as long: the case this describes is
    "a hard budget is spent", and the copy for it names no time — so treating it
    as the lesser of the two would promise a retry "shortly" that nothing
    guarantees.
    """
    if resets_at is None:
        return True
    try:
        return resets_at.astimezone(UTC) - (now or datetime.now(UTC)) > LONG_QUOTA_WINDOW
    except (AttributeError, TypeError, ValueError):
        return True


def is_long_quota_window(exc: Exception, now: datetime | None = None) -> bool:
    """:func:`is_long_window` for the ``resets_at`` an exception carries."""
    return is_long_window(getattr(exc, "resets_at", None), now)


class ProviderError(Exception):
    """Base exception for all provider errors.

    ``retryable=False`` marks the error as permanent: the publish engine
    fails the post immediately instead of scheduling backoff retries.
    """

    def __init__(
        self,
        message: str,
        platform: str = "",
        raw_response: dict | None = None,
        retryable: bool = True,
    ):
        self.platform = platform
        self.raw_response = raw_response or {}
        self.retryable = retryable
        super().__init__(message)


class OAuthError(ProviderError):
    """OAuth flow failure (invalid code, denied access, etc.)."""


class TokenExpiredError(ProviderError):
    """Access token has expired and refresh failed or is unavailable.

    ``status_code`` carries the HTTP status the platform answered with, and is
    load-bearing rather than decorative: ``apps.publisher.engine``'s
    ``_is_ambiguous_submission_failure`` and ``_is_retryable_first_comment_failure``
    both read it through ``getattr(exc, "status_code", None)`` and treat a
    missing code as "outcome unknown, do not retry". A 401 that used to arrive
    as ``APIError(status_code=401)`` must keep answering 401 here or a
    first comment silently flips from retryable to untouchable.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        **kwargs,
    ):
        self.status_code = status_code
        super().__init__(message, **kwargs)


class RateLimitError(ProviderError):
    """Platform rate limit exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        **kwargs,
    ):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class QuotaExceededError(RateLimitError):
    """A hard — usually daily — API quota is spent, not a per-second throttle.

    Subclasses :class:`RateLimitError` so every existing consumer keeps working
    unchanged: nothing sends the user to reconnect a perfectly healthy account,
    and the publish engine's two retry gates short-circuit on their
    ``isinstance(exc, RateLimitError)`` checks before they reach ``status_code``.

    It covers a momentary throttle as well as a spent daily budget, since both
    want the same circuit breaker. Callers that must tell the two apart — how
    loudly to log, what to tell the user — ask :func:`is_long_quota_window`
    rather than the class.

    ``resets_at`` is when the window rolls over, when the platform's quota has a
    knowable boundary (YouTube's resets at midnight US/Pacific). ``quota_scope``
    names *which* pool ran dry for platforms that meter more than one — YouTube
    charges the Data API, the Analytics API and video uploads against separate
    budgets, and conflating them would stop the cheap call because the
    expensive one failed.
    """

    def __init__(
        self,
        message: str,
        *,
        resets_at=None,
        status_code: int | None = None,
        quota_scope: str = "",
        **kwargs,
    ):
        self.resets_at = resets_at
        self.status_code = status_code
        self.quota_scope = quota_scope
        super().__init__(message, **kwargs)


class PublishError(ProviderError):
    """Post publishing failed."""


class APIError(ProviderError):
    """Generic API error from the platform."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        **kwargs,
    ):
        self.status_code = status_code
        super().__init__(message, **kwargs)
