# Behaviour is verified end-to-end, in a browser, against a real database

A feature is done when it is tested end-to-end.

The suite drives a real browser against the application served from a real PostgreSQL database, under the same Content Security Policy production enforces.

**The database is ephemeral and belongs to the run.** It is created when the session starts and destroyed when it ends. A test run must not require a database to have been provisioned first, must not need credentials, and must not leave anything behind.

**The e2e settings enforce what production enforces.** Any setting that is relaxed for local convenience - the CSP is the one that matters - is restored here. A harness configured more leniently than production reports success for defects that only production will meet.

**Unit tests are not a substitute.** The defect that motivated this requirement passed the ENTIRE unit suite, every static check, and `manage.py check`, because it only manifests when a browser applies a policy to a rendered page.

No test count is quoted here, deliberately. A number written into prose is a claim that stops being true the next time somebody adds a test, and this sentence had already outlived two of them. If you want the figure, run the suite - it is the only source that cannot be stale.
