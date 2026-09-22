import hashlib

from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

# Paths that are rate-limited for unauthenticated POST requests (auth flows)
AUTH_RATE_LIMITED_PATHS = (
    "/accounts/login/",
    "/accounts/signup/",
    "/accounts/password/reset/",
    "/accounts/password/reset/key/",
)

# Rate limit: 10 POST requests per minute per IP for auth endpoints
AUTH_RATE_LIMIT = 10
AUTH_RATE_WINDOW = 60  # seconds

EXEMPT_PATH_PREFIXES = (
    "/accounts/accept-terms/",
    "/accounts/logout/",
    "/accounts/google/",
    "/accounts/3rdparty/",
    "/health/",
    "/static/",
    # Uploaded media, served by config/urls.py when SERVE_MEDIA is on. No view
    # backs these URLs, so a redirect here just turns every <img>/<video> on
    # the accept-terms page into a 302 — and the platforms that fetch
    # attachment URLs server-side (see config/urls.py) are anonymous anyway.
    "/media/",
    "/admin/",
)


class TosAcceptanceMiddleware:
    """Redirect authenticated users to the ToS acceptance page if they haven't accepted yet."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Path check first: ``request.user`` is lazy, and touching it forces a
        # session read plus a user query. On an exempt path — /static/, /media/
        # — that work buys nothing, and media is requested once per file.
        if (
            not request.path.startswith(EXEMPT_PATH_PREFIXES)
            and hasattr(request, "user")
            and request.user.is_authenticated
            and request.user.tos_accepted_at is None
        ):
            return redirect(reverse("accounts:accept_terms"))

        return self.get_response(request)


class AuthRateLimitMiddleware:
    """Rate-limit POST requests to authentication endpoints (login, signup, password reset)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and any(request.path.startswith(p) for p in AUTH_RATE_LIMITED_PATHS):
            ip = self._get_client_ip(request)
            cache_key = f"auth_ratelimit:{hashlib.md5(ip.encode()).hexdigest()}"

            attempts = cache.get(cache_key, 0)
            if attempts >= AUTH_RATE_LIMIT:
                return HttpResponse("Too many requests. Please try again later.", status=429)

            cache.set(cache_key, attempts + 1, AUTH_RATE_WINDOW)

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
