"""Deploy checks for a Brown Creative Studio production install.

Run with ``python manage.py check --deploy``. ``deploy/deploy.sh`` runs it with
``--fail-level ERROR`` inside the freshly built image, so the errors here block
a deploy and the warnings are printed for a person to read.
"""

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

from apps.about.version import running_commit

_PLACEHOLDER_FROM = {"", "noreply@localhost", "noreply@yourdomain.com"}
_LOCAL_SMTP_HOSTS = {"", "localhost", "127.0.0.1"}


@register(Tags.security, deploy=True)
def check_studio_deployment(app_configs, **kwargs):
    messages = []

    # AGPL-3.0 section 13: the Source code link must reach the running version.
    if not settings.SOURCE_CODE_URL:
        messages.append(
            Error(
                "SOURCE_CODE_URL is not set, so the Source code link has nowhere to point.",
                hint="Set it to the public fork, e.g. https://github.com/<owner>/<repo>.",
                id="about.E001",
            )
        )
    elif not settings.SOURCE_CODE_URL.startswith("https://"):
        messages.append(
            Error(
                "SOURCE_CODE_URL must be an https:// URL that users can open.",
                id="about.E001",
            )
        )
    if not running_commit():
        messages.append(
            Error(
                "The running commit is unknown, so the Source code link cannot point at this version.",
                hint="Build the image with --build-arg SOURCE_COMMIT=$(git rev-parse HEAD); deploy/deploy.sh does this.",
                id="about.E002",
            )
        )

    if settings.SIGNUP_MODE == "open":
        messages.append(
            Warning(
                "SIGNUP_MODE=open lets anyone on the internet create an account.",
                hint="Use SIGNUP_MODE=invite.",
                id="about.W001",
            )
        )

    if settings.STORAGE_BACKEND.lower() != "s3":
        messages.append(
            Warning(
                "Media is stored on the local filesystem.",
                hint="Use STORAGE_BACKEND=s3 with S3-compatible storage, or make sure MEDIA_ROOT is a "
                "persistent, backed-up volume.",
                id="about.W002",
            )
        )

    if not getattr(settings, "SENTRY_DSN", ""):
        messages.append(
            Warning(
                "SENTRY_DSN is not set, so errors in production are not reported anywhere.",
                id="about.W003",
            )
        )

    if not settings.SUPPORT_EMAIL:
        messages.append(Warning("SUPPORT_EMAIL is not set.", id="about.W004"))

    if not settings.TERMS_URL or not settings.PRIVACY_URL:
        messages.append(
            Warning(
                "TERMS_URL or PRIVACY_URL is not set, so users see a 'not published yet' page instead of a policy.",
                hint="Publish the studio's terms and privacy policy and set both URLs.",
                id="about.W005",
            )
        )

    if getattr(settings, "INTELLIGENCE_ENABLED", False):
        messages.append(
            Warning(
                "BrightBean's hosted Intelligence add-on is enabled. This deployment keeps it off.",
                hint="Leave every INTELLIGENCE_* and STUDIO_* variable blank.",
                id="about.W006",
            )
        )

    # base.py only knows SMTP: any other EMAIL_BACKEND_TYPE silently selects the
    # console backend, which prints mail to the log instead of sending it.
    if settings.EMAIL_BACKEND_TYPE != "smtp":
        messages.append(
            Warning(
                f"EMAIL_BACKEND_TYPE={settings.EMAIL_BACKEND_TYPE!r} prints email to the log instead of sending it.",
                hint="Use EMAIL_BACKEND_TYPE=smtp with your provider's SMTP settings (Resend, Postmark, SES...).",
                id="about.W007",
            )
        )
    elif settings.DEFAULT_FROM_EMAIL in _PLACEHOLDER_FROM or getattr(settings, "EMAIL_HOST", "") in _LOCAL_SMTP_HOSTS:
        messages.append(
            Warning(
                "Outgoing email is not configured: DEFAULT_FROM_EMAIL is a placeholder or EMAIL_HOST is unset.",
                hint="Magic links, invitations and reminders all depend on email delivery.",
                id="about.W007",
            )
        )

    return messages
