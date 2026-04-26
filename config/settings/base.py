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
    "apps.background_task_config.BackgroundTaskConfig",
]

LOCAL_APPS = [
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Cache (used by rate limiting, session fallback)
REDIS_URL = env("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/brightbean"),
}

# Custom user model
AUTH_USER_MODEL = "accounts.User"

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
STATIC_URL = "static/"
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
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }
else:
    MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
    MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sites framework
SITE_ID = 1

# django-allauth
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Google OAuth for user login/signup (separate from PLATFORM_GOOGLE_* used for publishing)
GOOGLE_AUTH_CLIENT_ID = env("GOOGLE_AUTH_CLIENT_ID", default="")
GOOGLE_AUTH_CLIENT_SECRET = env("GOOGLE_AUTH_CLIENT_SECRET", default="")

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

if EMAIL_BACKEND_TYPE == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="localhost")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Tailwind
TAILWIND_APP_NAME = "theme"

# CSP - Alpine.js standard build requires unsafe-eval for inline expression
# evaluation. Styles use unsafe-inline because Tailwind utility classes are inline.
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-eval'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_MEDIA_SRC = ("'self'", "blob:")
CSP_FORM_ACTION = ("'self'", "https://accounts.google.com")
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
MEDIA_LIBRARY_MAX_VIDEO_SIZE = 1024 * 1024 * 1024  # 1GB
MEDIA_LIBRARY_MAX_BULK_UPLOAD = 50
MEDIA_LIBRARY_THUMBNAIL_SIZE = (400, 400)
MEDIA_LIBRARY_FFMPEG_TIMEOUT = 300  # 5 minutes
MEDIA_LIBRARY_MAX_CONCURRENT_TRANSCODES = 2

# Encryption key derivation salt - MUST be set per-deployment via environment
ENCRYPTION_KEY_SALT = env("ENCRYPTION_KEY_SALT", default="").encode("utf-8") or None

# Sentry
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )

# Platform credentials env vars (cloud version)
_META_CREDENTIALS = {
    "app_id": env("PLATFORM_FACEBOOK_APP_ID", default=""),
    "app_secret": env("PLATFORM_FACEBOOK_APP_SECRET", default=""),
}
_GOOGLE_CREDENTIALS = {
    "client_id": env("PLATFORM_GOOGLE_CLIENT_ID", default=""),
    "client_secret": env("PLATFORM_GOOGLE_CLIENT_SECRET", default=""),
}
_INSTAGRAM_PERSONAL_CREDENTIALS = {
    "app_id": env("PLATFORM_INSTAGRAM_APP_ID", default=""),
    "app_secret": env("PLATFORM_INSTAGRAM_APP_SECRET", default=""),
}
_LINKEDIN_CREDENTIALS = {
    "client_id": env("PLATFORM_LINKEDIN_CLIENT_ID", default=""),
    "client_secret": env("PLATFORM_LINKEDIN_CLIENT_SECRET", default=""),
}

PLATFORM_CREDENTIALS_FROM_ENV = {
    # Meta platforms - Facebook, Instagram, and Threads share the same app
    "facebook": _META_CREDENTIALS,
    "instagram": _META_CREDENTIALS,
    "threads": _META_CREDENTIALS,
    # Instagram (Personal) - uses Instagram Login with separate Instagram App credentials
    "instagram_personal": _INSTAGRAM_PERSONAL_CREDENTIALS,
    # LinkedIn - personal and company page variants share one Community Management API app
    "linkedin_personal": _LINKEDIN_CREDENTIALS,
    "linkedin_company": _LINKEDIN_CREDENTIALS,
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
}

# Webhook verification
FACEBOOK_WEBHOOK_VERIFY_TOKEN = env("FACEBOOK_WEBHOOK_VERIFY_TOKEN", default="")
YOUTUBE_WEBHOOK_SECRET = env("YOUTUBE_WEBHOOK_SECRET", default="")

# Rate limiting
RATELIMIT_ENABLE = not DEBUG
RATELIMIT_USE_CACHE = "default"
