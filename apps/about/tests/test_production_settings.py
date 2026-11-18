"""Production configuration: the deploy checks and the sign-up guard."""

import os
import subprocess
import sys

import pytest
from django.conf import settings as django_settings

from apps.about.checks import check_studio_deployment
from apps.about.version import running_commit

SHA = "14b92fc0123456789abcdef0123456789abcdef0"


def _ids(messages):
    return {m.id for m in messages}


@pytest.fixture
def production_ready(settings, tmp_path):
    settings.SOURCE_CODE_URL = "https://github.com/studio/brown-creative-studio"
    settings.SOURCE_COMMIT = SHA
    settings.SIGNUP_MODE = "invite"
    settings.STORAGE_BACKEND = "s3"
    settings.SENTRY_DSN = "https://key@sentry.example/1"
    settings.SUPPORT_EMAIL = "hello@studio.example"
    settings.TERMS_URL = "https://studio.example/terms"
    settings.PRIVACY_URL = "https://studio.example/privacy"
    settings.INTELLIGENCE_ENABLED = False
    settings.EMAIL_BACKEND_TYPE = "smtp"
    settings.EMAIL_HOST = "smtp.resend.com"
    settings.DEFAULT_FROM_EMAIL = "studio@studio.example"
    running_commit.cache_clear()
    yield settings
    running_commit.cache_clear()


def test_a_configured_deployment_passes(production_ready):
    assert check_studio_deployment(None) == []


def test_missing_source_url_is_an_error(production_ready):
    production_ready.SOURCE_CODE_URL = ""
    assert "about.E001" in _ids(check_studio_deployment(None))


def test_non_https_source_url_is_an_error(production_ready):
    production_ready.SOURCE_CODE_URL = "http://github.com/studio/repo"
    assert "about.E001" in _ids(check_studio_deployment(None))


def test_unknown_commit_is_an_error(production_ready, tmp_path):
    production_ready.SOURCE_COMMIT = ""
    production_ready.BASE_DIR = tmp_path
    running_commit.cache_clear()
    assert "about.E002" in _ids(check_studio_deployment(None))


@pytest.mark.parametrize(
    ("setting", "value", "check_id"),
    [
        ("SIGNUP_MODE", "open", "about.W001"),
        ("STORAGE_BACKEND", "local", "about.W002"),
        ("SENTRY_DSN", "", "about.W003"),
        ("SUPPORT_EMAIL", "", "about.W004"),
        ("TERMS_URL", "", "about.W005"),
        ("PRIVACY_URL", "", "about.W005"),
        ("INTELLIGENCE_ENABLED", True, "about.W006"),
        ("EMAIL_BACKEND_TYPE", "resend", "about.W007"),
        ("EMAIL_HOST", "localhost", "about.W007"),
        ("DEFAULT_FROM_EMAIL", "noreply@yourdomain.com", "about.W007"),
    ],
)
def test_each_gap_is_flagged(production_ready, setting, value, check_id):
    setattr(production_ready, setting, value)
    assert check_id in _ids(check_studio_deployment(None))


def _import_production_settings(**env):
    """Import config.settings.production in a fresh interpreter; return the completed process."""
    child_env = {
        **os.environ,
        "SECRET_KEY": "test-only-not-a-secret",
        "DATABASE_URL": "sqlite:////tmp/unused.db",
        **env,
    }
    return subprocess.run(
        [sys.executable, "-c", "import config.settings.production"],
        cwd=django_settings.BASE_DIR,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_production_refuses_open_signup():
    result = _import_production_settings(SIGNUP_MODE="open")
    assert result.returncode != 0
    assert "SIGNUP_MODE=open is not allowed in production" in result.stderr


@pytest.mark.parametrize("mode", ["invite", "closed"])
def test_production_accepts_restricted_signup(mode):
    result = _import_production_settings(SIGNUP_MODE=mode)
    assert result.returncode == 0, result.stderr
