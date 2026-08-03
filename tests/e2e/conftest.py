"""Fixtures for the end-to-end suite.

The suite owns its database. A PostgreSQL cluster is created in a temporary
directory when the session starts, listens on a port nobody else holds, and is
destroyed when the session ends. Nothing connects to a pre-existing server, so
there is no credential to configure, no shared state to collide with, and
nothing left behind.

Run it:

    make test-e2e

or directly:

    pytest -m e2e --ds=config.settings.e2e tests/e2e

The settings module is not optional. config/settings/e2e.py ENFORCES the
Content Security Policy; config/settings/test.py only reports it.
"""

import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

SUPERUSER = "postgres"
DATABASE_NAME = "brightbean_e2e"
READY_TIMEOUT_S = 60

#: How many times to try starting the cluster on a freshly chosen port.
PORT_ATTEMPTS = 3

#: Installed over CDP before the first byte of the page, so it is not itself
#: subject to the page's Content Security Policy. A recorder injected as an
#: inline <script> would be silenced by exactly the fault it exists to observe.
CSP_VIOLATION_RECORDER = """
window.__cspViolations = [];
document.addEventListener('securitypolicyviolation', function (event) {
    window.__cspViolations.push({
        directive: event.violatedDirective,
        blockedURI: event.blockedURI,
        sample: event.sample,
    });
});
"""


def pytest_collection_modifyitems(items):
    """Mark everything under this directory e2e, so no test file has to remember.

    The path check is load-bearing. A conftest hook is handed EVERY collected
    item, not only the ones beneath it, so without the check a plain `pytest`
    run would mark the entire unit suite e2e and the default `-m "not e2e"`
    would then deselect all of it.
    """
    here = Path(__file__).parent.resolve()
    for item in items:
        path = Path(item.path).resolve()
        if here == path.parent or here in path.parents:
            item.add_marker("e2e")


def _find_postgres_bin_dir() -> Path:
    """Locate initdb/pg_ctl.

    A VERSIONED INSTALL DIRECTORY FIRST, PATH only as a fallback - which is the
    opposite of the obvious order, on purpose.

    On Debian and Ubuntu `/usr/bin/initdb` and `/usr/bin/pg_ctl` are pg_wrapper
    shims that pick a cluster by their own rules rather than being one server's
    binaries. Taking PATH first therefore hands `-D` and `-o "-p PORT ..."` to a
    wrapper on the assumption it behaves like the real thing, and skips the
    version selection below entirely - in exactly the environment where more
    than one major is likely to be installed, which is CI.

    Preferring the versioned directory makes the choice explicit and reachable.
    PATH still covers an install somewhere non-standard.
    """
    if os.name == "nt":
        roots = [Path(r"C:\Program Files\PostgreSQL")]
        pattern = "*/bin/initdb.exe"
    else:
        roots = [Path("/usr/lib/postgresql")]
        pattern = "*/bin/initdb"
    found = [p.parent for root in roots if root.is_dir() for p in root.glob(pattern)]
    if not found:
        on_path = shutil.which("initdb")
        if on_path:
            return Path(on_path).parent
        raise RuntimeError("no PostgreSQL binaries on PATH or in the usual install locations")

    def version(path):
        """Parse the version directory name, so 18 sorts above 9.6.

        These names are versions, not words. Sorted as STRINGS - which is what
        this did - "9.6" beats "18" beats "16" beats "10", so on any host with
        more than one server installed the harness picked the OLDEST. Locally
        there is exactly one install, so the sort is a no-op and the suite
        passing proves nothing about this branch; on GitHub's runner, where the
        image may already carry a major before apt installs another, which one
        gets used would not be decided by anything anybody chose.
        """
        try:
            return tuple(int(part) for part in path.parent.name.split("."))
        except ValueError:
            # Not a version at all - a vendor directory, a symlink farm. Rank it
            # below everything that does parse rather than crashing the session.
            return (-1,)

    return sorted(found, key=version)[-1]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_to_completion(cmd, *, sink=None):
    """Run a command to completion, raising on a non-zero exit.

    `sink` names a file to receive the child's output. Pass it for anything
    that leaves a daemon behind: `pg_ctl start` hands its standard handles to
    the postgres it spawns, and the server holds them open for its entire life,
    so a pipe here never reaches EOF and the caller blocks forever. `-l` does
    not help - that redirects the server's log, not the inherited handles.

    Output is decoded with errors="replace" because postgres speaks the
    operating system's language, which is not necessarily UTF-8.
    """
    if sink is not None:
        with open(sink, "ab") as handle:
            completed = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, check=False)
        output = ""
    else:
        completed = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", check=False)
        output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} failed ({completed.returncode}):\n{output}")
    return output


def _can_connect(port: int) -> bool:
    import psycopg

    try:
        with psycopg.connect(host="127.0.0.1", port=port, user=SUPERUSER, dbname="postgres", connect_timeout=3):
            return True
    except Exception:
        return False


def _wait_until_ready(port: int) -> None:
    """Poll until the cluster accepts a real connection.

    Readiness is proven by connecting rather than by trusting `pg_ctl -w`,
    because what the suite needs to know is whether psycopg can talk to it.
    """
    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline:
        if _can_connect(port):
            return
        time.sleep(0.3)
    raise RuntimeError(f"cluster did not accept connections within {READY_TIMEOUT_S}s")


@pytest.fixture(scope="package", autouse=True)
def allow_sync_orm_on_the_browser_greenlet():
    """Let synchronous ORM calls run while a Playwright greenlet is on the stack.

    Playwright's synchronous API drives the browser from a greenlet running on
    an asyncio loop, so Django sees "an async context" and refuses every
    synchronous ORM call. That breaks pytest-django's own teardown, which
    flushes the database after a live_server test - the tests pass and the run
    still exits non-zero. The loop belongs to the browser driver, not to the
    application, so a blocking query on it cannot starve anything that matters.

    AUTOUSE AND SCOPED TO THIS DIRECTORY, DEFINED IN THIS CONFTEST, WHICH IS
    THE WHOLE POINT. An earlier version set the variable at module level. pytest imports
    every conftest it walks past during COLLECTION, and mark-based deselection
    happens afterwards - so a plain `pytest` run, which is what `make test` and
    CI both run, imported this file and turned Django's async-safety guard off
    for all 1072 unit tests. Nothing could catch that: the variable can only
    ever REMOVE failures, so every gate stayed green while a real
    SynchronousOnlyOperation in application code would have passed the suite
    and raised only in production.

    PACKAGE scope, not session. An autouse fixture scoped to this directory
    runs only when a test in this directory does - but a SESSION-scoped one is
    finalised at the END OF THE SESSION, not when this directory's tests
    finish. Under `-m ""` or a nightly "run everything" job, that leaves the
    guard disarmed for every unit test collected after the first e2e test - the
    module-level failure mode described above, narrowed but not removed. Package
    scope makes teardown symmetric with setup, which is what was meant.

    The previous value is restored, so nothing leaks back out to a caller that
    had set it deliberately.
    """
    previous = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
        else:
            os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = previous


def _stop_cluster_immediately(binaries: Path, datadir: Path) -> None:
    subprocess.run(
        [str(binaries / "pg_ctl"), "-D", str(datadir), "-m", "immediate", "-w", "stop"],
        capture_output=True,
        check=False,
    )


@pytest.fixture(scope="session")
def ephemeral_postgres():
    """Create a PostgreSQL cluster for this session; destroy it afterwards."""
    binaries = _find_postgres_bin_dir()
    workdir = Path(tempfile.mkdtemp(prefix="brightbean-e2e-pg-"))
    datadir = workdir / "data"
    started = False
    port = 0
    try:
        _run_to_completion(
            [
                str(binaries / "initdb"),
                "-D",
                str(datadir),
                "-U",
                SUPERUSER,
                "--auth-local=trust",
                "--auth-host=trust",
                "--encoding=UTF8",
                "--no-sync",
            ]
        )
        # A FRESH PORT PER ATTEMPT, because _free_port cannot reserve one.
        # It binds a socket, reads the number the kernel chose and closes it
        # again - so between that and pg_ctl binding, anything else on the host
        # may take it. On a developer machine that is rare enough never to have
        # been seen; on a shared CI runner it is a classic flake, and the e2e
        # job now blocks every merge, so one flake is indistinguishable from a
        # real environmental failure. Retrying is cheaper than diagnosing that.
        for attempt in range(PORT_ATTEMPTS):
            port = _free_port()
            try:
                # No quoted values in -o. A quoted one is passed through
                # verbatim and the server rejects its own configuration; that
                # is the bug which makes pytest-postgresql unusable on Windows.
                _run_to_completion(
                    [
                        str(binaries / "pg_ctl"),
                        "-D",
                        str(datadir),
                        "-l",
                        str(workdir / "postgres.log"),
                        "-o",
                        f"-p {port} -F -c listen_addresses=127.0.0.1",
                        "-w",
                        "start",
                    ],
                    sink=workdir / "pg_ctl.log",
                )
                started = True
                _wait_until_ready(port)
                break
            except RuntimeError:
                if started:
                    _stop_cluster_immediately(binaries, datadir)
                    started = False
                if attempt == PORT_ATTEMPTS - 1:
                    raise
        yield {"host": "127.0.0.1", "port": port, "user": SUPERUSER}
    finally:
        if started:
            _stop_cluster_immediately(binaries, datadir)
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture(scope="session")
def django_db_modify_db_settings(ephemeral_postgres):
    """Point Django at the ephemeral cluster before the test database is built.

    pytest-django's own `django_db_setup` depends on this fixture by name, so
    overriding it here is all that is needed to get the ordering right. The
    settings are mutated in place, which is what pytest-django's own xdist
    variant does, and happens before any connection is opened.
    """
    from django.conf import settings

    settings.DATABASES["default"].update(
        {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DATABASE_NAME,
            "USER": ephemeral_postgres["user"],
            "PASSWORD": "",
            "HOST": ephemeral_postgres["host"],
            "PORT": ephemeral_postgres["port"],
        }
    )


@pytest.fixture
def csp_page(page):
    """A Playwright page that records CSP violations from before the first byte."""
    page.add_init_script(CSP_VIOLATION_RECORDER)
    return page
