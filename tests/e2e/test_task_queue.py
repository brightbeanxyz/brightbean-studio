"""End-to-end: the background worker still works on Django 6.0.7.

THIS IS THE GATE CARRYING THIS MIGRATION'S LARGEST SINGLE ASSUMPTION.

`django-background-tasks` 1.2.8 predates Django 5 entirely, and this migration
moves the framework from 5.1 to 6.0.7 while KEEPING it. Everything deferred in
this application runs through it - publishing, inbox sync, notification
retries, media processing, analytics, scheduled organization deletions. If its
ORM paths break on 6.0, none of that happens, and the web application stays
perfectly green while it does not happen.

That risk was carried for a long time on an import smoke test, which
established only that the package LOADS and that `manage.py check` passes, and
which said so in its own limits. This is that check promoted from a workspace
probe that does not ship into a gate that runs on every push.

It uses the real worker command, and lets it find the work on its own.
"""

import pytest
from background_task import background
from background_task.models import CompletedTask, Task
from django.core.management import call_command

#: Appended to by the task below, IN THIS PROCESS, so the test can prove the
#: function body ran rather than only that a row moved between tables. A worker
#: that marks work done without doing it is the failure that matters.
MARKERS_RECORDED_BY_THE_TASK: list[str] = []


@background(schedule=0)
def record_that_it_ran(marker):
    MARKERS_RECORDED_BY_THE_TASK.append(marker)


@pytest.mark.django_db(transaction=True)
def test_the_worker_executes_enqueued_work_on_django_6():
    """Enqueue through the decorator, run the worker, prove the body ran.

    `--duration` bounds the worker's life. There is no `--once`: `process_tasks`
    loops until it is killed, which is also why nothing in this repository can
    check its exit code for a failed pass - it does not have one.
    """
    MARKERS_RECORDED_BY_THE_TASK.clear()
    record_that_it_ran("e2e")

    assert Task.objects.filter(task_name__endswith="record_that_it_ran").exists(), (
        "the @background call wrote no row - the decorator is not reaching the database"
    )

    call_command("process_tasks", "--duration", "5")

    assert MARKERS_RECORDED_BY_THE_TASK == ["e2e"], "the row was consumed, but the function never ran"

    completed = CompletedTask.objects.filter(task_name__endswith="record_that_it_ran").first()
    assert completed is not None, "the task never reached CompletedTask"
    assert completed.failed_at is None, f"the worker recorded a failure: {completed.last_error}"
