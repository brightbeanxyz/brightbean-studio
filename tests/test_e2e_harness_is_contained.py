"""The e2e harness must not change how the UNIT suite behaves.

`DJANGO_ALLOW_ASYNC_UNSAFE` tells Django to permit synchronous ORM calls from
an async context. The e2e harness genuinely needs it - Playwright's synchronous
API drives the browser from a greenlet on an asyncio loop - and sets it from an
autouse fixture scoped to tests/e2e, so it is armed only while those tests run.

It was once set at MODULE level in that conftest instead. pytest imports every
conftest it walks past during COLLECTION and applies mark deselection
afterwards, so a plain `pytest` run - which is what `make test` and CI both run
- imported the file and disarmed Django's async-safety guard for the entire
unit suite. A real SynchronousOnlyOperation in application code would have
passed the suite and raised only in production.

Nothing could catch that by running tests, because the variable can only ever
REMOVE failures: every gate stayed green precisely because it was broken.

So this checks the source instead of the behaviour. That is deliberate. An
assertion about `os.environ` cannot distinguish "leaked at import" from "a
legitimate e2e fixture is active in this session", and would be flaky the first
time somebody ran both suites together. The regression has one shape - an
assignment at module level - and this pins that shape exactly.
"""

from pathlib import Path

E2E_CONFTEST_PATH = Path(__file__).parent / "e2e" / "conftest.py"

ASYNC_SAFETY_OVERRIDE_ENV_VAR = "DJANGO_ALLOW_ASYNC_UNSAFE"


def test_the_e2e_conftest_does_not_disarm_async_safety_at_import_time():
    source = E2E_CONFTEST_PATH.read_text(encoding="utf-8")

    assert ASYNC_SAFETY_OVERRIDE_ENV_VAR in source, (
        f"{ASYNC_SAFETY_OVERRIDE_ENV_VAR} is not mentioned in {E2E_CONFTEST_PATH.name} at all. Either the harness "
        f"stopped needing it - in which case delete this test - or the file moved "
        f"and this test now guards nothing."
    )

    at_module_level = [
        line
        for line in source.splitlines()
        if ASYNC_SAFETY_OVERRIDE_ENV_VAR in line and line[:1] not in {" ", "\t", "#"}
    ]

    assert not at_module_level, (
        f"{E2E_CONFTEST_PATH.name} touches {ASYNC_SAFETY_OVERRIDE_ENV_VAR} at module level: {at_module_level}. "
        f"pytest imports this conftest during collection of ANY run, so that "
        f"disarms Django's async-safety guard for the whole unit suite. Set it "
        f"from a fixture scoped to tests/e2e instead."
    )
