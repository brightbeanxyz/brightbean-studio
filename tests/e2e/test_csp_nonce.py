"""End-to-end regression test for the Content Security Policy nonce.

Django 6.0 keeps the nonce private on the request as `_csp_nonce` and publishes
it to templates as `{{ csp_nonce }}`. The django-csp spelling this project used
to carry, `{{ request.csp_nonce }}`, is a missing attribute - and Django
resolves a missing attribute to the empty string rather than raising. Every
inline script then renders `nonce=""` and is refused by a script-src that
lists a nonce: Alpine never initialises, the htmx wiring never binds, and the
page loads and does nothing.

Nothing else in this repository catches it. It passes `git apply`, compileall,
ruff, `manage.py check` and the entire unit suite, and it cannot be reproduced
against the dev or test settings, which run the policy report-only - where a
violating script is reported and then executed anyway.

Two levels, deliberately:

  * the served bytes, which needs no browser and localises a failure to the
    template layer;
  * a real browser under an enforcing policy, which is the only thing that
    proves the page actually works.
"""

import re
import urllib.request

#: Anonymous, always present, and rendered through templates/base.html - so it
#: carries the inline scripts the nonce has to cover.
NONCE_BEARING_PAGE_PATH = "/accounts/login/"

NONCED_SCRIPT_TAG_RE = re.compile(r"<script[^>]*\snonce=\"([^\"]*)\"", re.IGNORECASE)


def _fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def test_inline_scripts_carry_a_non_empty_nonce(live_server):
    """The bytes on the wire carry a real nonce.

    Checked here rather than in the browser because browsers strip the nonce
    attribute from the DOM - it is observable only in the response body.
    """
    html = _fetch(live_server.url + NONCE_BEARING_PAGE_PATH)
    nonces = NONCED_SCRIPT_TAG_RE.findall(html)

    assert nonces, "no <script nonce=...> in the response at all"
    empty = [value for value in nonces if not value.strip()]
    assert not empty, f'{len(empty)} of {len(nonces)} inline scripts rendered nonce=""'
    assert len(set(nonces)) == 1, f"one response must carry one nonce, saw {len(set(nonces))}"


#: django-ninja renders this page from its own template, loaded by absolute
#: path, rather than through a view that calls render(request, ...). Whether
#: the csp context processor runs for it is therefore a property of ninja's
#: internals, not of this codebase - which makes it the one nonce site that
#: reading the diff cannot settle. Guessing it is how `{{ request.csp_nonce }}`
#: survived into a tree where it renders empty, which is the defect this module
#: exists to catch.
API_DOCS_PAGE_PATH = "/api/v1/docs"


def test_the_api_docs_page_carries_a_real_nonce(live_server):
    html = _fetch(live_server.url + API_DOCS_PAGE_PATH)
    nonces = NONCED_SCRIPT_TAG_RE.findall(html)

    assert nonces, f"no <script nonce=...> at {API_DOCS_PAGE_PATH} at all"
    empty = [value for value in nonces if not value.strip()]
    assert not empty, (
        f'{len(empty)} of {len(nonces)} inline scripts on {API_DOCS_PAGE_PATH} rendered nonce="". '
        f"django-ninja renders this template outside the normal view path, so the csp "
        f"context processor did not run for it - which blocks every script on the docs "
        f"page under an enforcing policy."
    )


def test_browser_reports_no_csp_violations(live_server, csp_page):
    """A real browser executes the page without the policy refusing anything.

    Waiting on window.Alpine is a positive control: it proves scripts genuinely
    ran, so an empty violation list cannot be mistaken for a page that never
    loaded.
    """
    csp_page.goto(live_server.url + NONCE_BEARING_PAGE_PATH, wait_until="domcontentloaded")
    csp_page.wait_for_function("window.Alpine !== undefined", timeout=15000)

    violations = csp_page.evaluate("window.__cspViolations || []")

    assert violations == [], f"the browser refused {len(violations)} resource(s): {violations}"
