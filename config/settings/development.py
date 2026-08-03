import os as _os

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# CSRF trust for HTTPS tunnels (ngrok, cloudflared, etc.) used during local
# Intelligence integration testing. Django requires the request Origin /
# Referer host to be explicitly trusted for any POST coming through a
# non-localhost hostname, even with DEBUG=True. Reads STUDIO_BASE_URL if
# set (the integration's https-required env var) so you don't have to
# remember a second env knob — anything else can go into CSRF_TRUSTED_ORIGINS
# explicitly via env. Wildcarded scheme: HTTPS only.
_csrf_trusted = []
_studio_base = _os.environ.get("STUDIO_BASE_URL", "").strip().rstrip("/")
if _studio_base.startswith("https://"):
    _csrf_trusted.append(_studio_base)
# Extra hosts (comma-separated) e.g. "https://foo.ngrok-free.app,https://bar"
_extra = _os.environ.get("CSRF_TRUSTED_ORIGINS", "").strip()
if _extra:
    _csrf_trusted.extend(o.strip() for o in _extra.split(",") if o.strip())
if _csrf_trusted:
    CSRF_TRUSTED_ORIGINS = _csrf_trusted

# Tunnel-aware redirect handling. ngrok terminates TLS and forwards plain
# HTTP to runserver; without this Django treats requests as http:// and
# Stripe's success URL redirect → activate view would build wrong scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Plain storage in dev — no manifest needed, runserver uses finders directly.
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}

# Use console email backend in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Report-only CSP: violations are reported, nothing is blocked.
# Django 6.0 expresses this as a separate setting rather than a flag,
# so the policy is moved wholesale onto the report-only key. Assigning
# from CSP_POLICY rather than from SECURE_CSP keeps this a definition
# rather than a read of a name this module also rebinds.
#
# Note that this makes a blocked-script defect impossible to reproduce
# here. The e2e suite therefore runs its own enforcing settings.
SECURE_CSP = None
SECURE_CSP_REPORT_ONLY = CSP_POLICY  # noqa: F405

# Django debug toolbar (optional)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

SESSION_COOKIE_SECURE = False
