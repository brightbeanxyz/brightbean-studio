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

# Console email in development. EMAIL_BACKEND stays the budget wrapper from
# base.py so the real send path is what runs locally, but the caps are off
# (negative = unlimited): the console backend exists to show you every message,
# and inheriting the production 6-per-recipient-per-hour would silently swallow
# the seventh with nothing but a log line — for the rest of the hour, since the
# counters are in the database and survive a restart. Set them to real values
# locally when the budget itself is what you are testing.
EMAIL_INNER_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_DAILY_SEND_LIMIT = -1
EMAIL_RECIPIENT_HOURLY_LIMIT = -1
EMAIL_RECIPIENT_DAILY_LIMIT = -1

# Disable CSP in development
CSP_REPORT_ONLY = True

# Django debug toolbar (optional)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

SESSION_COOKIE_SECURE = False
