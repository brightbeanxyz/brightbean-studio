import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENCRYPTION_KEY_SALT", "test-salt-not-for-production")

from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

# Use faster password hasher in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# In-memory email. Django's setup_test_environment() overwrites EMAIL_BACKEND
# with locmem for the whole run (django/test/utils.py), so the budget wrapper is
# bypassed here unless a test asks for it back with
# @override_settings(EMAIL_BACKEND="apps.common.mail.BudgetedEmailBackend").
# That is what apps/common/tests/test_mail_budget.py does. The limits are
# negative (unlimited) so a test that opts in meets only the caps it sets.
EMAIL_INNER_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_DAILY_SEND_LIMIT = -1
EMAIL_RECIPIENT_HOURLY_LIMIT = -1
EMAIL_RECIPIENT_DAILY_LIMIT = -1

# Disable CSP in tests
CSP_REPORT_ONLY = True

# Use local storage in tests. STORAGES must be reset too, not just the flag:
# base.py already picked the backend from the *environment*, so on a machine
# whose .env sets STORAGE_BACKEND=s3 the suite was quietly running against the
# real S3 backend while this said "local" — making storage-dependent tests pass
# or fail according to the developer's .env rather than the code. MEDIA_URL and
# SERVE_MEDIA are pinned for the same reason: that s3 branch leaves the first
# unset and the second False, so without them a local run and a CI run would
# disagree about whether /media/ is routed at all.
STORAGE_BACKEND = "local"
STORAGES["default"] = {  # noqa: F405
    "BACKEND": "django.core.files.storage.FileSystemStorage",
}
MEDIA_ROOT = BASE_DIR / "test_media"  # noqa: F405
MEDIA_URL = "/media/"
SERVE_MEDIA = True

# Use simple static files storage in tests (no manifest/collectstatic needed)
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "brightbean_test",
        "USER": env("DB_USER", default="postgres"),  # noqa: F405
        "PASSWORD": env("DB_PASSWORD", default="postgres"),  # noqa: F405
        "HOST": env("DB_HOST", default="localhost"),  # noqa: F405
        "PORT": env.int("DB_PORT", default=5432),  # noqa: F405
    },
}
