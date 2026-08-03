# CSP is provided by core Django, not django-csp

Django 6.0 moved CSP into core (`django.middleware.csp.ContentSecurityPolicyMiddleware`, `SECURE_CSP`).

The alternative was upgrading `django-csp` 3.8 -> 4.x, which itself required rewriting flat `CSP_*` settings into a nested dict. Since the settings had to be rewritten either way, the version that removes a dependency was chosen.

**Two hazards, recorded because both are quiet.**

`@csp_update` appended to one directive. `@csp_override` does not replace one directive - it replaces the ENTIRE policy. The middleware uses the decorator's dict instead of `SECURE_CSP` and merges nothing, so `@csp_override({"form-action": [...]})` serves a page whose only directive is `form-action`: no `script-src`, no `default-src`, and therefore no restriction on scripts whatsoever - on the OAuth consent screen and the account-connection flows. Measured against `django/middleware/csp.py`, and pinned by `tests/test_csp_overrides.py`, which discovers every routed `@csp_override` site from the URLconf. The **three** converted sites splat `settings.CSP_POLICY` and replace one key. Do not shorten them to just the directive being widened.

There were four `@csp_update` decorators, not three. The fourth - on the onboarding OAuth start view - is DELETED rather than converted: every one of the ten hosts it appended is already in the base `form-action` list, so under django-csp's append semantics its effective policy was the base policy. That was settled by set membership against the two lists, not by reading the code and judging it harmless. Reproducing it as an override would have shipped a decorator whose presence claims an effect it does not have.

`request.csp_nonce` does not exist in core Django - the nonce lives at `request._csp_nonce` and reaches templates as `{{ csp_nonce }}`. The old spelling degrades to an empty string rather than raising, which blocks every inline script in production while every static check, the unit suite and the local dev server all stay green. This is the defect the e2e suite exists to catch.
