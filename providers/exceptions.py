"""Exception hierarchy for social platform providers."""


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
    """Access token has expired and refresh failed or is unavailable."""


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
