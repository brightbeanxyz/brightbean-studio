"""Every @csp_override in this application still serves the WHOLE policy.

`csp_override` does not override a DIRECTIVE - it replaces the entire policy.
django/middleware/csp.py reads the decorator dict INSTEAD of SECURE_CSP and
merges nothing, so a decorator carrying only `form-action` leaves that page
with no `script-src` and no `default-src` - which places no restriction on
scripts at all, on exactly the pages that hand control to a third party.

tests/e2e/test_csp_policy.py holds that down for ONE view, /oauth/authorize/,
because it is the only override site reachable without a login and a fixture.
The others are account-connection flows behind auth, and a site added next
year is covered by nothing at all.

This finds the sites itself, so the property holds for every one of them -
present and future - with no browser, no auth and no fixtures.

HOW. django/views/decorators/csp.py closes its wrapper over `config_attr_name`
and `config_attr_value`, and `@wraps` leaves `__wrapped__` pointing at what it
wrapped, so the dict a site WILL serve is readable straight off the closure.
Cells are read BY NAME off `co_freevars`; reading them positionally would
quietly return the wrong one if those were ever reordered.

Reaching into another package's closure is unusual and it is deliberate: the
alternative is authenticating and driving every flow, which is precisely what
left these sites uncovered. If a future Django renames those free variables
this stops finding anything - and the first test fails and says so, rather
than the rest passing vacuously against an empty list.

Only the ENFORCING slot is examined. Nothing here uses
`csp_report_only_override`, which stores `_csp_ro_config`; if that changes it
needs its own pass.
"""

from django.conf import settings
from django.urls import get_resolver

#: The OAuth consent screen and the two account-connection flows. A FLOOR, not
#: an equality - adding a fourth site should not fail a test about whether the
#: existing three are correct.
KNOWN_OVERRIDE_SITES = 3


def _free_variables(func):
    """The closure of `func`, by name. Empty for anything that has no closure."""
    code = getattr(func, "__code__", None)
    closure = getattr(func, "__closure__", None)
    if code is None or not closure:
        return {}
    return dict(zip(code.co_freevars, closure, strict=True))


def _read_csp_override_config(view):
    """The policy dict a csp_override on `view` will serve, or None.

    Walks the `__wrapped__` chain, so an override sitting UNDER another
    decorator - `@login_required` above `@csp_override` - is still found.
    """
    seen = set()
    while view is not None and id(view) not in seen:
        seen.add(id(view))
        cells = _free_variables(view)
        name, config = cells.get("config_attr_name"), cells.get("config_attr_value")
        if name is not None and config is not None:
            try:
                if name.cell_contents == "_csp_config":
                    return config.cell_contents
            except ValueError:
                pass  # an empty cell is not the decorator we are looking for
        view = getattr(view, "__wrapped__", None)
    return None


def _routes(resolver, prefix=""):
    """Every routed callable, descending through include()."""
    for entry in resolver.url_patterns:
        route = prefix + str(entry.pattern)
        if hasattr(entry, "url_patterns"):
            yield from _routes(entry, route)
        else:
            yield route, entry.callback


def find_routed_csp_override_sites():
    """Every routed view carrying a csp_override, as (route, config) pairs."""
    sites = []
    for route, callback in _routes(get_resolver()):
        config = _read_csp_override_config(callback)
        if config is not None:
            sites.append((route, config))
    return sites


def test_the_override_sites_are_still_discoverable():
    """Guards the assertion below against passing vacuously.

    If Django changes how csp_override stores its config, or the last override
    is deleted, the next test has nothing to check and would report success.
    """
    sites = find_routed_csp_override_sites()

    assert len(sites) >= KNOWN_OVERRIDE_SITES, (
        f"found {len(sites)} csp_override site(s), expected at least {KNOWN_OVERRIDE_SITES}. "
        f"Either a site was removed, or the way csp_override stores its config changed "
        f"and this file can no longer see any of them - in which case the policy check "
        f"below proves nothing."
    )


def test_every_override_serves_the_whole_policy():
    """An override must WIDEN the base policy, never replace or narrow it.

    A directive being present is not enough: a config that keeps the key and
    empties it is just as broken. Every source the base policy allows must
    survive, which is what splatting it and widening one directive produces.

    A page that genuinely needs to TIGHTEN a directive fails here. For a
    security policy that is the intended outcome - narrowing one should be a
    deliberate, visible act, not something that arrives as a green test.
    """
    base = settings.CSP_POLICY

    for route, config in find_routed_csp_override_sites():
        absent = [directive for directive in base if directive not in config]
        assert not absent, (
            f"/{route} overrides the CSP and drops {absent} entirely. csp_override "
            f"replaces the whole policy, so this page would be served with no "
            f"restriction on scripts at all. Splat settings.CSP_POLICY and replace "
            f"only the directive being widened."
        )
        for directive, allowed in base.items():
            dropped = [value for value in allowed if value not in config[directive]]
            assert not dropped, (
                f"/{route} overrides the CSP and drops {dropped} from {directive!r}, which the base policy allows."
            )
