# The background task library is kept, not replaced

**Chosen:** keep `django-background-tasks` 1.2.8.

Moving to Django 6.0 does not require replacing it, and that was measured rather than assumed. Driven against the real tree on 6.0.7 with a real PostgreSQL: its migrations apply, a `@background` call writes a row, and `process_tasks` executed all eleven recurring jobs the `post_migrate` hooks register - every one finishing with no failure recorded.

**Core `django.tasks` was not adopted, and it is not a near miss.** Django 6.0 ships the task CONTRACT - `@task`, `Task.enqueue`, `TaskResult` - and two backends, `immediate` and `dummy`. There is no durable backend and no scheduler in core. Adopting it therefore means writing and owning a database-backed runner and a periodic scheduler: a project with its own concurrency failure modes, not a step in a framework upgrade.

**Three properties of the retained worker, measured.** None is a regression - all three are true of the system today - but nothing in this repository stated them, and each one turns an outage into a silent one.

- `process_tasks` **exits 0 when the database is unreachable.** It prints `Failed to retrieve tasks. Database unreachable.` and returns success. Anything watching exit codes sees green while no work is running at all.
- It has **no single-pass mode.** It loops until killed, so there is no invocation whose exit code could be checked even in principle; `--duration` is the only way to make it return.
- **Every `repeat=` task re-queues itself on completion**, and the `post_migrate` hooks re-register any that are missing. The `background_task` table therefore never drains, so any procedure that says "wait until the queue is empty" waits forever.

Revisit this when core Django gains a durable backend, or when the library stops working on a supported Django. Not before.
