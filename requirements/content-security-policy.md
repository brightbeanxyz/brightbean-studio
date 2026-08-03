# The application enforces a Content Security Policy

A CSP is enforced on every response in production, and reported-only in development and test.

Inline scripts carry the request nonce. Templates read it as `{{ csp_nonce }}`, published by `django.template.context_processors.csp`. The nonce is **not** available as `request.csp_nonce` - Django keeps it private - and the template language resolves a missing attribute to the empty string, so getting this wrong disables every inline script with no error anywhere.

Views that hand control to an external OAuth provider must extend `form-action` to include that provider's post-consent redirect target. Chromium enforces `form-action` across the entire redirect chain, so omitting the target breaks the flow with no visible error.

Such a view must serve the WHOLE policy, not just the directive it widens. `@csp_override` replaces the entire policy rather than merging into it, so a decorator carrying only `form-action` leaves that page with no `script-src` and no `default-src` - which places no restriction on scripts at all, on exactly the pages that hand control to a third party. Extensions splat `settings.CSP_POLICY` and replace one key.
