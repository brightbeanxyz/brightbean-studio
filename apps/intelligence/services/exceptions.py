"""Typed exceptions surfaced by the Intelligence clients.

View code should catch these directly rather than inspecting HTTP
status codes, so the error → UI mapping lives in one place.
"""

from __future__ import annotations


class IntelligenceClientError(Exception):
    """Base class, anything client-call-related."""

    status_code: int | None = None
    code: str | None = None

    def __init__(
        self, message: str = "", *, status_code: int | None = None, code: str | None = None, body: dict | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.body = body or {}


class InvalidApiKey(IntelligenceClientError):
    """401, the per-org bearer key was rejected."""


class InsufficientCredits(IntelligenceClientError):
    """402, Intelligence returned credits=0; show upgrade CTA."""


class RateLimited(IntelligenceClientError):
    """429, caller is over plan rate limit."""

    def __init__(self, *args, retry_after: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ServiceUnavailable(IntelligenceClientError):
    """5xx / network error, transient."""


class BadRequest(IntelligenceClientError):
    """4xx that isn't covered by a more specific subclass."""


class NotFound(IntelligenceClientError):
    """404, typically "no pending activation" or "no account"."""


class Conflict(IntelligenceClientError):
    """409, idempotency / eligibility blocker."""

    def __init__(self, *args, retry_after: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ActivationRejected(IntelligenceClientError):
    """4xx from /activate-preflight or /activate-commit, payment problem,
    metadata mismatch, unknown_checkout_attempt, etc."""

    @property
    def user_message(self) -> str:
        # Map known codes to copy a user can act on.
        return {
            "metadata_missing_studio_source": ("This Stripe session was not initiated through Studio."),
            "deployment_mismatch": ("This Stripe session was created by a different Studio deployment."),
            "client_reference_mismatch": ("The Stripe session's org reference doesn't match this org."),
            "price_not_allowlisted": ("The plan you paid for isn't currently sold by this deployment."),
            "not_paid": "Stripe is still processing your payment.",
            "session_not_found": "We couldn't find your Stripe payment session.",
            "session_incomplete": (
                "Your Stripe checkout isn't complete yet. Finish payment in Stripe, then come back."
            ),
            "wrong_mode": (
                "This Stripe session isn't a subscription. Start a new checkout "
                "from the Activate page to create a subscription."
            ),
            "no_line_items": ("Your Stripe session has no plan attached. Start a new checkout from the Activate page."),
            "unknown_checkout_attempt": (
                "We can't find a checkout we initiated for this payment. "
                "If you just paid, please refresh the page in a moment."
            ),
            "token_expired": ("Your activation token expired. Please refresh and try again."),
            "token_already_consumed": ("This activation has already been processed. Please refresh."),
            "missing_subscription_id": (
                "Stripe didn't return a subscription for this session. Start a new checkout from the Activate page."
            ),
            "unknown_plan": (
                "The plan attached to this Stripe session isn't recognised. "
                "Pick a plan from the Activate page to start a fresh checkout."
            ),
            "unmapped_price": (
                "The price you paid isn't currently mapped to a plan. Please contact support so we can reconcile it."
            ),
            "no_pending_activation": (
                "We don't have a pending activation for this organisation. Start a new checkout from the Activate page."
            ),
            "session_id_mismatch": (
                "The Stripe session you provided doesn't match the pending activation for this organisation."
            ),
            "invalid_token": ("Your activation token isn't valid. Please refresh and try again."),
            "token_deployment_mismatch": (
                "Your activation token was minted by a different deployment. Please refresh and try again."
            ),
        }.get(self.code or "", "We couldn't complete activation. Please contact support.")


class DeploymentNotAuthorized(IntelligenceClientError):
    """401/403 indicating the deployment is not registered or is disabled."""


class OrgAuthorizationMismatch(Exception):
    """The resolved_external_org_id from Intelligence doesn't match the
    expected org. Raised by the local activate view, not Intelligence.
    """
