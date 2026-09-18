from pathlib import Path
from urllib.parse import urlparse

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    APP_URL=(str, "http://localhost:8000"),
    STORAGE_BACKEND=(str, "local"),
    EMAIL_BACKEND_TYPE=(str, "smtp"),
    SENTRY_DSN=(str, ""),
    REDIS_URL=(str, ""),
)

environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
APP_URL = env("APP_URL")

# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_htmx",
    "tailwind",
    "csp",
    # OAuth 2.1 Authorization Server backing the MCP connector flow.
    "oauth2_provider",
    "apps.background_task_config.BackgroundTaskConfig",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.organizations",
    "apps.workspaces",
    "apps.members",
    "apps.settings_manager",
    "apps.credentials",
    "apps.social_accounts",
    "apps.media_library",
    "apps.composer",
    "apps.calendar",
    "apps.publisher",
    "apps.notifications",
    "apps.inbox",
    "apps.approvals",
    "apps.client_portal",
    "apps.onboarding",
    # Always installed (migrations consistent across deployments). URLs +
    # templates short-circuit when ``settings.INTELLIGENCE_ENABLED`` is False,
    # so self-hosters who don't set the Intelligence env vars get no
    # Stripe / billing surface at all.
    "apps.intelligence",
    "apps.api_keys",
    "apps.api",
    "apps.mcp",
    "apps.oauth_server",
    "apps.analytics",
    "theme",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.accounts.middleware.AuthRateLimitMiddleware",
    "apps.accounts.middleware.TosAcceptanceMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.members.middleware.RBACMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.notifications.context_processors.unread_notification_count",
                "apps.common.context_processors.sidebar_context",
                "apps.onboarding.context_processors.onboarding_checklist",
                "apps.intelligence.context_processors.intelligence_flag",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Cache (used by rate limiting, session fallback)
#
# The "filmstrip" alias holds the composer frame picker's strips: ~8 base64
# JPEGs each, orders of magnitude larger than anything else we cache. It is a
# separate alias so those entries can never crowd out the cache everyone else
# shares — but it is spelled out per backend rather than derived from
# ``default``, because ``LOCATION`` means different things to the two: a bare
# namespace for LocMemCache, and the *connection URL* for RedisCache. Copying
# ``default`` and overriding LOCATION would point the Redis alias at a server
# named "filmstrip" and fail every frame-picker request on any deployment that
# sets REDIS_URL.
REDIS_URL = env("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        },
        # Shared and out of the web process entirely; Redis's own eviction
        # policy bounds it, so no MAX_ENTRIES here (LocMem-only anyway).
        "filmstrip": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "filmstrip",
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        # In-process and per gunicorn worker, so this one has to be bounded:
        # the default MAX_ENTRIES of 300 would be tens of MB of resident
        # memory on a box already tight for it.
        "filmstrip": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "filmstrip",
            "OPTIONS": {"MAX_ENTRIES": 32, "CULL_FREQUENCY": 2},
        },
    }

# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/brightbean"),
}

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Agent API trusted-proxy list — IPs whose ``X-Forwarded-For`` header we
# will honour for client-IP derivation in the rate-limit throttle and
# audit log. Empty by default so the API uses ``REMOTE_ADDR`` directly,
# which is the only safe choice when the app is reached without a
# trusted proxy in front. Set ``BB_TRUSTED_PROXIES`` in the environment
# (comma-separated) when you run the app behind Cloudflare, an ALB,
# nginx, etc.
BB_TRUSTED_PROXIES = tuple(p.strip() for p in env.list("BB_TRUSTED_PROXIES", default=[]) if p.strip())

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
]

# Password hashing - bcrypt with cost factor 12
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
STORAGE_BACKEND = env("STORAGE_BACKEND")
if STORAGE_BACKEND.lower() == "s3":
    # Object storage hands out its own presigned URLs; this process never
    # serves MEDIA_ROOT, so the env var is deliberately ignored here.
    SERVE_MEDIA = False
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    }
    AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="")
    AWS_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("S3_BUCKET_NAME", default="")
    AWS_S3_CUSTOM_DOMAIN = env("S3_CUSTOM_DOMAIN", default="")
    AWS_S3_REGION_NAME = env("S3_REGION_NAME", default="auto")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = "private"
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600  # 1-hour expiry for presigned URLs
    # django-storages spools every object it READS into a SpooledTemporaryFile
    # sized by this setting. Its own default is 0 — and CPython's spool check is
    # ``if max_size and pos > max_size``, so 0 is falsy and the spool NEVER rolls
    # over to disk: each read holds the whole object in the process heap, and the
    # freed buffer is not returned to the OS. A 120 MB video cost 120 MB of
    # permanent RSS, which is what pushed the Heroku worker past its quota into an
    # R15 kill mid-publish. Any non-zero value makes the spool behave as intended.
    AWS_S3_MAX_MEMORY_SIZE = env.int("AWS_S3_MAX_MEMORY_SIZE", default=2 * 1024 * 1024)
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }
else:
    # Local FS fallback so dev + test environments without S3 credentials
    # can still call default_storage / save uploaded files.
    STORAGES["default"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    }
    MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
    MEDIA_URL = "/media/"
    SERVE_MEDIA = env.bool("SERVE_MEDIA", default=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sites framework
SITE_ID = 1

# django-allauth
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"
ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"

# Who may create an account. Applies to both the email form and social
# logins; signing in with an existing account is never affected.
#
#   open    anyone can sign up (default — unchanged behaviour)
#   invite  only visitors who followed a valid invitation link
#   closed  nobody; accounts are created in the Django admin
#
# A deployment reachable from the internet — which it has to be, so the
# platforms can deliver OAuth callbacks and webhooks — is open to the world
# on "open". Self-hosters usually want "invite".
SIGNUP_MODE = env("SIGNUP_MODE", default="open").strip().lower()
if SIGNUP_MODE not in {"open", "invite", "closed"}:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        f"SIGNUP_MODE must be one of open, invite, closed — got {SIGNUP_MODE!r}. "
        "Refusing to guess, because falling back to a default would silently "
        "leave signup open."
    )

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Google OAuth for user login/signup (separate from PLATFORM_GOOGLE_* used for publishing)
GOOGLE_AUTH_CLIENT_ID = env("GOOGLE_AUTH_CLIENT_ID", default="")
GOOGLE_AUTH_CLIENT_SECRET = env("GOOGLE_AUTH_CLIENT_SECRET", default="")

# Unsplash stock-photo search in the composer (optional; empty disables the feature)
UNSPLASH_ACCESS_KEY = env("UNSPLASH_ACCESS_KEY", default="")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_AUTH_CLIENT_ID,
            "secret": GOOGLE_AUTH_CLIENT_SECRET,
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "VERIFIED_EMAIL": True,
    },
}

SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = False
ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.SocialAccountAdapter"

# Sessions
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60  # 14 days
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = True  # Sliding window

# Email
EMAIL_BACKEND_TYPE = env("EMAIL_BACKEND_TYPE")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@localhost")

# Everything outbound goes through the budget wrapper, which then hands the
# message to EMAIL_INNER_BACKEND. There is no send_email() helper in this
# codebase — six places build EmailMultiAlternatives inline and allauth builds
# its own — so this is the only point where a runaway loop can be stopped.
EMAIL_BACKEND = "apps.common.mail.BudgetedEmailBackend"

if EMAIL_BACKEND_TYPE == "smtp":
    EMAIL_INNER_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="localhost")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
else:
    EMAIL_INNER_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Outbound email budget (apps/common/mail.py). A negative limit means unlimited
# and 0 means send nothing — that way round on purpose, so that an operator
# typing 0 mid-incident gets what they plainly meant. Counters are kept either
# way, because the count is what tells us where the limit belongs.
# EMAIL_SENDING_ENABLED=false is the blunt lever, and needs a config change
# rather than a deploy.
EMAIL_SENDING_ENABLED = env.bool("EMAIL_SENDING_ENABLED", default=True)
EMAIL_DAILY_SEND_LIMIT = env.int("EMAIL_DAILY_SEND_LIMIT", default=2000)
EMAIL_RECIPIENT_HOURLY_LIMIT = env.int("EMAIL_RECIPIENT_HOURLY_LIMIT", default=6)
EMAIL_RECIPIENT_DAILY_LIMIT = env.int("EMAIL_RECIPIENT_DAILY_LIMIT", default=20)
RESEND_WEBHOOK_SECRET = env("RESEND_WEBHOOK_SECRET", default="")

# Invitations. The cooldown and the send cap live on the Invitation row so they
# survive a cache flush; the per-org daily cap uses the email budget counters.
INVITE_RESEND_COOLDOWN_SECONDS = env.int("INVITE_RESEND_COOLDOWN_SECONDS", default=300)
INVITE_MAX_SENDS = env.int("INVITE_MAX_SENDS", default=3)
INVITE_MAX_PER_ORG_PER_DAY = env.int("INVITE_MAX_PER_ORG_PER_DAY", default=25)

# Tailwind
TAILWIND_APP_NAME = "theme"

# CSP - Alpine.js standard build requires unsafe-eval for inline expression
# evaluation. Styles use unsafe-inline because Tailwind utility classes are inline.
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-eval'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "blob:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'", "https://cdn.jsdelivr.net")
CSP_MEDIA_SRC = ("'self'", "blob:")
CSP_FORM_ACTION = (
    "'self'",
    "https://accounts.google.com",
    "https://checkout.stripe.com",
    "https://billing.stripe.com",
    "https://www.facebook.com",
    "https://api.instagram.com",
    "https://www.instagram.com",
    "https://www.threads.com",
    "https://threads.net",
    "https://www.linkedin.com",
    "https://www.pinterest.com",
    "https://www.tiktok.com",
)
CSP_INCLUDE_NONCE_IN = ["script-src"]

# Allow media/images from the storage domain in CSP
if STORAGE_BACKEND.lower() == "s3":
    _storage_origin = AWS_S3_CUSTOM_DOMAIN or AWS_S3_ENDPOINT_URL
    if _storage_origin:
        if not _storage_origin.startswith("https://"):
            _storage_origin = f"https://{_storage_origin}"
        _parsed = urlparse(_storage_origin)
        _storage_origin = f"{_parsed.scheme}://{_parsed.hostname}"
        CSP_MEDIA_SRC = (*CSP_MEDIA_SRC, _storage_origin)  # type: ignore[assignment]
        CSP_IMG_SRC = (*CSP_IMG_SRC, _storage_origin)  # type: ignore[assignment]

# Media Library
MEDIA_LIBRARY_MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
# The ceiling that actually bounds memory. A 20 MB file says nothing about how
# many pixels it expands to, and a palette PNG being converted for resampling
# peaks near 5 bytes per pixel, so 30M px is ~150 MB — the spike budget a
# 512 MB worker has left once the app itself is resident.
#
# Pillow's own decompression-bomb check does NOT cover this: it only *warns*
# between 1x and 2x MAX_IMAGE_PIXELS and raises above 2x, leaving a window that
# decodes to over 500 MB. ``apps.media_library.services`` checks this itself,
# and does it AFTER ``Image.draft()`` — a 61 MP JPEG is cheap because the JPEG
# decoder downscales during the read, so rejecting it on its header dimensions
# would refuse a file that never costs us the memory. What this really bounds
# is the formats that have no draft support (PNG, WebP, GIF) and the edit path,
# which needs full resolution by definition.
MEDIA_LIBRARY_MAX_IMAGE_PIXELS = 30_000_000
MEDIA_LIBRARY_MAX_VIDEO_SIZE = 1024 * 1024 * 1024  # 1GB
MEDIA_LIBRARY_MAX_BULK_UPLOAD = 50
MEDIA_LIBRARY_THUMBNAIL_SIZE = (400, 400)
MEDIA_LIBRARY_FFMPEG_TIMEOUT = 300  # 5 minutes
MEDIA_LIBRARY_MAX_CONCURRENT_TRANSCODES = 2
MEDIA_LIBRARY_PRESIGN_EXPIRE = 900  # seconds a presigned direct-upload URL stays valid

# Storage quota — bounds the total bytes a single Organization can
# accumulate in the media library. Without this, an Agent API key with
# ``upload_media`` permission could fill the bucket unbounded.
#
# Resolution order at runtime (high → low precedence):
#   1. OrgSetting ``media.storage_quota_bytes_override`` (manual support
#      exception or enterprise contract).
#   2. ``STORAGE_QUOTA_TIERS[IntelligenceSubscription.plan_slug]``.
#   3. ``STORAGE_QUOTA_DEFAULT``.
# See ``apps.media_library.quotas.resolve_storage_quota``.
STORAGE_QUOTA_ENABLED = env.bool("STORAGE_QUOTA_ENABLED", default=True)
STORAGE_QUOTA_TIERS = {
    # plan_slug → bytes. Slugs must match values produced by Intelligence.
    "hobby": 5 * 1024**3,  # 5 GB
    "creator": 50 * 1024**3,  # 50 GB
    "agency": 500 * 1024**3,  # 500 GB
}
STORAGE_QUOTA_DEFAULT = 5 * 1024**3  # 5 GB fallback for orgs without an active subscription

# Encryption key derivation salt - MUST be set per-deployment via environment
ENCRYPTION_KEY_SALT = env("ENCRYPTION_KEY_SALT", default="").encode("utf-8") or None

# Sentry
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk

    # Both rates are env-tunable because the profiler keeps stack samples in
    # memory, which a 512 MB dyno cannot spare. Profiling defaults to off; turn
    # it on deliberately when you are actually chasing a regression.
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        profiles_sample_rate=env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.0),
    )

# Platform credentials env vars (cloud version)
_META_CREDENTIALS = {
    "app_id": env("PLATFORM_FACEBOOK_APP_ID", default=""),
    "app_secret": env("PLATFORM_FACEBOOK_APP_SECRET", default=""),
    # Optional Facebook Login for Business configuration. When present Meta
    # controls the permission and business-asset selection through this config.
    "config_id": env("PLATFORM_FACEBOOK_CONFIG_ID", default=""),
}
_GOOGLE_CREDENTIALS = {
    "client_id": env("PLATFORM_GOOGLE_CLIENT_ID", default=""),
    "client_secret": env("PLATFORM_GOOGLE_CLIENT_SECRET", default=""),
}
_INSTAGRAM_LOGIN_CREDENTIALS = {
    "app_id": env("PLATFORM_INSTAGRAM_APP_ID", default=""),
    "app_secret": env("PLATFORM_INSTAGRAM_APP_SECRET", default=""),
}
# Threads has its own app identity: a Meta app carrying the "Access the Threads
# API" use case gets a Threads App ID / Secret distinct from the Facebook pair
# (App settings -> Basic -> Threads App ID). Sending the Facebook App ID to
# threads.com/oauth/authorize fails with error 4476002 ("No app ID was provided
# in the request"), so these deliberately do NOT fall back to _META_CREDENTIALS.
# Left unset, Threads stays unconfigured and resolves through the org's
# admin-entered PlatformCredential row instead.
_THREADS_CREDENTIALS = {
    "app_id": env("PLATFORM_THREADS_APP_ID", default=""),
    "app_secret": env("PLATFORM_THREADS_APP_SECRET", default=""),
}
_LINKEDIN_LEGACY_CLIENT_ID = env("PLATFORM_LINKEDIN_CLIENT_ID", default="")
_LINKEDIN_LEGACY_CLIENT_SECRET = env("PLATFORM_LINKEDIN_CLIENT_SECRET", default="")

# LinkedIn Company always uses Community Management API scopes (the only path that
# works for Company Pages). Falls back to legacy shared creds for backward compat.
_LINKEDIN_COMPANY_CREDENTIALS = {
    "client_id": env("PLATFORM_LINKEDIN_COMPANY_CLIENT_ID", default="") or _LINKEDIN_LEGACY_CLIENT_ID,
    "client_secret": env("PLATFORM_LINKEDIN_COMPANY_CLIENT_SECRET", default="") or _LINKEDIN_LEGACY_CLIENT_SECRET,
}

# LinkedIn Personal credential resolution + auto-derived OAuth mode:
#   1. PLATFORM_LINKEDIN_PERSONAL_* set -> dedicated personal app -> OIDC + Share scopes
#      (the only personal-posting tier obtainable without CM approval)
#   2. Else, reuse the company app -> CM scopes (refresh tokens + inbox supported)
#   3. Else, empty placeholder
# `_oauth_mode` is computed here, never user-set; it lives in the credentials dict
# so the provider can branch on it without importing settings.
_LINKEDIN_PERSONAL_CLIENT_ID = env("PLATFORM_LINKEDIN_PERSONAL_CLIENT_ID", default="")
if _LINKEDIN_PERSONAL_CLIENT_ID:
    _LINKEDIN_PERSONAL_CREDENTIALS = {
        "client_id": _LINKEDIN_PERSONAL_CLIENT_ID,
        "client_secret": env("PLATFORM_LINKEDIN_PERSONAL_CLIENT_SECRET", default=""),
        "_oauth_mode": "oidc",
    }
elif _LINKEDIN_COMPANY_CREDENTIALS["client_id"]:
    _LINKEDIN_PERSONAL_CREDENTIALS = {
        **_LINKEDIN_COMPANY_CREDENTIALS,
        "_oauth_mode": "community_management",
    }
else:
    # No LinkedIn env vars set. Keep `_oauth_mode` out so the dict carries nothing
    # but the empty required keys — `_get_configured_platforms()` and
    # `resolve_platform_credentials()` both gate on `derive_is_configured`, which
    # reads only client_id / client_secret. The provider defaults to OIDC mode
    # via `_is_oidc_mode` if it ever sees an empty credentials dict.
    _LINKEDIN_PERSONAL_CREDENTIALS = {"client_id": "", "client_secret": ""}

PLATFORM_CREDENTIALS_FROM_ENV = {
    # Meta platforms - Facebook and Instagram share the same app
    "facebook": _META_CREDENTIALS,
    "instagram": _META_CREDENTIALS,
    # Threads runs on the same Meta app but a different app identity - see
    # _THREADS_CREDENTIALS above and the README "Meta" section.
    "threads": _THREADS_CREDENTIALS,
    # Instagram (Direct) - uses Instagram Login with separate Instagram App credentials.
    # Despite the platform key, this targets Professional (Business/Creator) IG accounts
    # without requiring a linked Facebook Page. See providers/instagram_login.py.
    "instagram_login": _INSTAGRAM_LOGIN_CREDENTIALS,
    # LinkedIn - personal can run on its own OIDC + Share app (Path A) or reuse the
    # company app's Community Management API credentials (Path B). See README.
    "linkedin_personal": _LINKEDIN_PERSONAL_CREDENTIALS,
    "linkedin_company": _LINKEDIN_COMPANY_CREDENTIALS,
    "tiktok": {
        "client_key": env("PLATFORM_TIKTOK_CLIENT_KEY", default=""),
        "client_secret": env("PLATFORM_TIKTOK_CLIENT_SECRET", default=""),
    },
    # Google platforms - YouTube and Google Business Profile share the same OAuth client
    "youtube": _GOOGLE_CREDENTIALS,
    "google_business": _GOOGLE_CREDENTIALS,
    "pinterest": {
        "app_id": env("PLATFORM_PINTEREST_APP_ID", default=""),
        "app_secret": env("PLATFORM_PINTEREST_APP_SECRET", default=""),
    },
    # Bluesky - session-based auth (app passwords), no app-level credentials needed
    "bluesky": {},
    # Mastodon - instance-specific OAuth; credentials are registered per-instance
    # on first connect and persisted in MastodonAppRegistration. No repo-wide
    # credentials apply.
    "mastodon": {},
    # DEV.to - per-account API key (no OAuth). The key is supplied by the user
    # at connect time, so no app-level credentials apply (same as Bluesky).
    "devto": {},
}

# Publishing engine
# How long after a post goes live the first comment is attempted, and how many
# times a failed attempt is retried. Both were previously read via getattr()
# from settings that did not exist, so neither could be tuned or overridden.
PUBLISHER_FIRST_COMMENT_DELAY = env.int("PUBLISHER_FIRST_COMMENT_DELAY", default=120)
PUBLISHER_FIRST_COMMENT_MAX_RETRIES = env.int("PUBLISHER_FIRST_COMMENT_MAX_RETRIES", default=3)
# How long a PlatformPost may sit in ``publishing`` before the confirmation sweep
# gives up on it. STALE applies to a row we never got a platform handle for —
# the worker died mid-publish and nothing will ever finish it. CONFIRM applies to
# a row whose platform (TikTok) accepted the upload and is still processing it;
# that legitimately takes minutes, so it gets a much longer leash.
PUBLISHER_STALE_PUBLISHING_TIMEOUT = env.int("PUBLISHER_STALE_PUBLISHING_TIMEOUT", default=900)
PUBLISHER_PUBLISH_CONFIRM_TIMEOUT = env.int("PUBLISHER_PUBLISH_CONFIRM_TIMEOUT", default=1800)
# Publisher concurrency. MAX_CONCURRENT_PUBLISHES is a row limit on the due
# query; the other two are a *Postgres connection budget*. Every thread the
# publish engine spawns takes its own connection (Django connections are
# thread-local), so POSTS + PLATFORM_PUBLISHES plus the web dyno's gunicorn
# threads have to stay under the connection limit the whole database ROLE gets.
# That is 20 on heroku-postgresql:essential-0, which a per-group platform pool
# exceeded on its own and took production down on 2026-09-15. Raise these only
# alongside the Postgres plan. Like the timeouts above, they were read via
# getattr() from settings that did not exist, so none could be tuned.
PUBLISHER_MAX_CONCURRENT_PUBLISHES = env.int("PUBLISHER_MAX_CONCURRENT_PUBLISHES", default=10)
PUBLISHER_MAX_CONCURRENT_POSTS = env.int("PUBLISHER_MAX_CONCURRENT_POSTS", default=4)
PUBLISHER_MAX_CONCURRENT_PLATFORM_PUBLISHES = env.int("PUBLISHER_MAX_CONCURRENT_PLATFORM_PUBLISHES", default=6)

# Webhook verification
FACEBOOK_WEBHOOK_VERIFY_TOKEN = env("FACEBOOK_WEBHOOK_VERIFY_TOKEN", default="")
INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN = env("INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN", default="")
YOUTUBE_WEBHOOK_SECRET = env("YOUTUBE_WEBHOOK_SECRET", default="")

# Rate limiting
RATELIMIT_ENABLE = not DEBUG
RATELIMIT_USE_CACHE = "default"


# ---------------------------------------------------------------------------
# OAuth 2.1 Authorization Server (django-oauth-toolkit) — MCP connector flow
# ---------------------------------------------------------------------------
# Powers the /api/v1/mcp endpoint's native connector flow: an MCP client
# (e.g. Claude Desktop) registers itself via Dynamic Client Registration,
# then runs an authorization-code + PKCE flow against /oauth/authorize/ and
# /oauth/token/. Issued access tokens resolve to a User and act with that
# user's current workspace permissions. Existing bb_studio_ API keys keep
# working unchanged (Claude Code injects them as a static header).
#
# Studio serves the app, the API, and the OAuth server on ONE host, so both
# URLs default to APP_URL (unlike a split app/api deployment).
#   MCP_PUBLIC_BASE_URL  — origin advertised as the /mcp resource server.
#   MCP_OAUTH_ISSUER_URL — origin of the OAuth Authorization Server (where
#     /oauth/authorize/ sends unauthenticated users to log in via allauth).
MCP_PUBLIC_BASE_URL = env("MCP_PUBLIC_BASE_URL", default=APP_URL).rstrip("/")
MCP_OAUTH_ISSUER_URL = env("MCP_OAUTH_ISSUER_URL", default=APP_URL).rstrip("/")

OAUTH2_PROVIDER = {
    "SCOPES": {"mcp": "Call BrightBean Studio MCP tools on your behalf"},
    "DEFAULT_SCOPES": ["mcp"],
    "PKCE_REQUIRED": True,
    # Restrict ``code_challenge_method`` to ``S256``. django-oauth-toolkit
    # (and oauthlib under it) accept ``plain`` by default — RFC 7636 §4.2
    # marks ``plain`` as insecure. ``S256OnlyOAuth2Validator`` rejects any
    # authorize request whose method is missing or ``plain`` before a Grant
    # row is written.
    "OAUTH2_VALIDATOR_CLASS": "apps.oauth_server.validator.S256OnlyOAuth2Validator",
    "ACCESS_TOKEN_EXPIRE_SECONDS": 60 * 60,
    "REFRESH_TOKEN_EXPIRE_SECONDS": 30 * 24 * 60 * 60,
    "AUTHORIZATION_CODE_EXPIRE_SECONDS": 600,
    "ROTATE_REFRESH_TOKEN": True,
    "REQUEST_APPROVAL_PROMPT": "auto",
    # Claude's OAuth callback is always https; reject non-TLS redirect URIs.
    "ALLOWED_REDIRECT_URI_SCHEMES": ["https"],
}


# ---------------------------------------------------------------------------
# Intelligence integration (optional hosted SaaS)
# ---------------------------------------------------------------------------
# All five env vars must be set for the integration to be active. Missing
# any one → INTELLIGENCE_ENABLED is False and the entire surface is hidden:
# no left-nav item, no /orgs/<id>/intelligence/ URLs, no /intelligence/
# routes. Self-hosters who don't set these get vanilla OSS Studio.
INTELLIGENCE_INTERNAL_URL = env("INTELLIGENCE_INTERNAL_URL", default="")
INTELLIGENCE_PUBLIC_URL = env("INTELLIGENCE_PUBLIC_URL", default="")
STUDIO_DEPLOYMENT_ID = env("STUDIO_DEPLOYMENT_ID", default="")
STUDIO_SHARED_SECRET = env("STUDIO_SHARED_SECRET", default="")
STUDIO_BASE_URL = env("STUDIO_BASE_URL", default="")

INTELLIGENCE_ENABLED = all(
    [
        INTELLIGENCE_INTERNAL_URL.strip(),
        INTELLIGENCE_PUBLIC_URL.strip(),
        STUDIO_DEPLOYMENT_ID.strip(),
        STUDIO_SHARED_SECRET.strip(),
        STUDIO_BASE_URL.strip(),
    ]
)

if INTELLIGENCE_ENABLED:
    # Security invariants — raised (not asserted) because ``python -O``
    # strips assertions. Open-redirect defense + Stripe success-URL
    # constraint + bearer-key-transit confidentiality all depend on
    # these being enforced at boot rather than per-request.
    from urllib.parse import urlparse as _urlparse

    from django.core.exceptions import ImproperlyConfigured

    if not STUDIO_BASE_URL.startswith("https://"):
        raise ImproperlyConfigured("STUDIO_BASE_URL must be https:// when Intelligence is enabled.")

    # The Intelligence URLs carry sensitive material in BOTH directions:
    # /activate-commit and /rotate-key return plaintext API keys in the
    # response body, and every /v1/* tool call sends the per-org bearer
    # in the Authorization header. Plain http would leak both to any
    # observer on the wire. Require https:// in production while still
    # allowing http://localhost or http://127.0.0.1 for local dev (the
    # ngrok-fronted Studio talks to a loopback Intelligence over plain
    # HTTP — same machine, same kernel, no wire to observe).
    def _is_secure_intelligence_url(url: str) -> bool:
        if url.startswith("https://"):
            return True
        try:
            host = (_urlparse(url).hostname or "").lower()
        except ValueError:
            return False
        return host in {"localhost", "127.0.0.1", "::1"}

    for _name, _url in (
        ("INTELLIGENCE_INTERNAL_URL", INTELLIGENCE_INTERNAL_URL),
        ("INTELLIGENCE_PUBLIC_URL", INTELLIGENCE_PUBLIC_URL),
    ):
        if not _is_secure_intelligence_url(_url):
            raise ImproperlyConfigured(
                f"{_name} must be https:// (http:// is only accepted for "
                f"localhost / 127.0.0.1 dev tunnels) — current value would "
                f"leak Intelligence API keys in transit."
            )
