"""Database-connection discipline for threads the application spawns itself.

Django connections are thread-local and are closed automatically on exactly one
event: the ``request_finished`` signal. Nothing off the request path fires it,
so any thread this project starts — a ``ThreadPoolExecutor`` worker, a timer —
has to hand its connection back itself. Release is otherwise left to the
garbage collector reclaiming the thread-local wrapper, which is not guaranteed
and which a reference cycle (a traceback held by a log record, say) can defer
indefinitely.

That matters because the ceiling is shared and small: on
``heroku-postgresql:essential-0`` the whole database ROLE gets 20 connections
across every dyno. Publishing exhausted them on 2026-09-15 and took the site
down — see ``apps.publisher.engine`` for the fan-out that did it.
"""

from django.db import connections


def in_worker_thread(fn, *args, **kwargs):
    """Run ``fn`` as the whole body of a spawned thread, closing its connection after.

    Wrap the callable submitted to a pool, not the pool itself: the point is
    that the connection goes back when *this unit of work* ends, including when
    it raises, which is exactly when a leaked connection goes unnoticed.
    """
    try:
        return fn(*args, **kwargs)
    finally:
        connections.close_all()


def release_idle_connection() -> None:
    """Hand back connections this thread is about to stop using for a while.

    For the stretch inside a worker where the work is all network I/O — a video
    upload, a provider poll — and the database is untouched. Holding a
    connection across it costs one connection per in-flight worker for the
    duration of the slowest call.

    Connections inside an atomic block are left alone. Django's ``close()``
    deliberately skips ``validate_no_atomic_block()`` and instead flags the
    connection ``needs_rollback``, so closing under a caller's transaction would
    silently doom it rather than fail loudly. A caller holding a transaction is
    also, by definition, not idle on the database.
    """
    for conn in connections.all(initialized_only=True):
        if not conn.in_atomic_block:
            conn.close()
