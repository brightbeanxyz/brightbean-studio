"""Brown Creative Studio settings, layered over BrightBean's ``base.py``.

``base.py`` star-imports this module on its last line, so every settings module
(development, production, test) sees these values and can still override them.
Keeping the fork's settings here, rather than spread through upstream's file,
keeps upstream merges small. See CHANGES.md.

Nothing here may hold a secret: every value is either a public fact about the
deployment or read from the environment.
"""

import environ

# base.py has already loaded .env into os.environ (read_env), so a bare Env
# sees the same values without reading the file a second time.
_env = environ.Env()

# ── Studio identity ──────────────────────────────────────────────────────────
# Shown in page titles, emails and the django.contrib.sites record (allauth puts
# Site.name into email subjects). apps.about syncs that record after migrate.
SITE_NAME = _env("SITE_NAME", default="Brown Creative Studio").strip()

# Where users are told to write for help. Blank is allowed in development; the
# deploy check (about.W004) flags it in production.
SUPPORT_EMAIL = _env("SUPPORT_EMAIL", default="").strip()

# The studio's published policies. Blank serves in-app pages that say the policy
# has not been published yet; never BrightBean's documents.
TERMS_URL = _env("TERMS_URL", default="").strip()
PRIVACY_URL = _env("PRIVACY_URL", default="").strip()

# ── Corresponding source (AGPL-3.0 section 13) ───────────────────────────────
# Every studio and portal user sees a "Source code" link. It must lead to the
# source of the version that is actually running, so it is built from:
#   SOURCE_CODE_URL  the public fork, e.g. https://github.com/<owner>/<repo>
#   SOURCE_COMMIT    the commit the image was built from. The Docker build sets
#                    it from a build argument; without it, apps.about reads
#                    .git in the working copy (development only).
SOURCE_CODE_URL = _env("SOURCE_CODE_URL", default="").strip().rstrip("/")
SOURCE_COMMIT = _env("SOURCE_COMMIT", default="").strip()

# The project this fork is based on, credited on the source page.
UPSTREAM_PROJECT_NAME = "BrightBean Studio"
UPSTREAM_SOURCE_URL = "https://github.com/brightbeanxyz/brightbean-studio"
SOFTWARE_LICENSE = "AGPL-3.0"
