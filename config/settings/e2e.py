"""Settings for the end-to-end suite: the test settings, with CSP ENFORCED.

That single difference is the reason this module exists.

config/settings/test.py runs the Content Security Policy in report-only mode.
Under report-only a violating inline script is reported to the console and then
executed anyway, so the page works and a broken policy is invisible. An e2e
suite that inherited those settings would pass happily against a tree in which
every inline script is refused in production.

Do not "simplify" this file by deleting the two lines that swap the policy back.
They are the entire point of it.
"""

from .test import *  # noqa: F403

# test.py runs the policy report-only. Enforce it here, so the browser really
# refuses what production refuses. Taken from CSP_POLICY rather than from
# SECURE_CSP_REPORT_ONLY so this reads as "e2e enforces the base policy",
# which is the intent, instead of a swap between two names.
SECURE_CSP = CSP_POLICY  # noqa: F405
SECURE_CSP_REPORT_ONLY = None

# live_server speaks plain HTTP. A redirect to https would end every test
# before it reached a page.
SECURE_SSL_REDIRECT = False

# live_server binds an arbitrary port on localhost.
ALLOWED_HOSTS = ["*"]
