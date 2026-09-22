"""Regression cover for the ``InboxReply`` draft-lifecycle migrations.

Two separate contracts are covered here.

1. The migrations must apply to a table that **already has rows**. ``0002``
   adds ``status`` with ``db_index=True``, and Django does not emit that
   ``CREATE INDEX`` inline — ``schema_editor.add_field()`` defers it to the
   schema editor's ``__exit__``, i.e. after every operation in the migration
   has run. While the backfill lived in ``0002``, its ``UPDATE``s left pending
   FK trigger events on ``inbox_reply`` (Django makes FK constraints
   ``DEFERRABLE INITIALLY DEFERRED``), and Postgres refuses to build an index
   on a relation in that state::

       cannot CREATE INDEX "inbox_reply" because it has pending trigger events

   An empty table hides this — 0 rows updated queues no trigger events — which
   is why the suite stayed green while production's release phase died.

2. The backfill must be safe to run *late*. It reached staging inside ``0002``
   but reaches other databases as ``0004``, by which time real drafts and
   failed replies exist. Only rows that were genuinely delivered may be
   touched.
"""

from __future__ import annotations

import functools
import importlib
from datetime import timedelta

import pytest
from django.apps import apps as global_apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from apps.inbox.models import InboxReply

APP = "inbox"
INITIAL = "0001_initial"
SCHEMA = "0002_inboxreply_draft_lifecycle"

backfill = importlib.import_module("apps.inbox.migrations.0004_backfill_inboxreply_status")


@functools.cache
def _head() -> str:
    """Name of the inbox app's latest migration.

    Cached: the graph is built from files on disk, which do not change during
    a run, and building one loads every migration in the project.
    """
    return MigrationExecutor(connection).loader.graph.leaf_nodes(APP)[0][1]


def _index_defs() -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT indexdef FROM pg_indexes WHERE tablename = 'inbox_reply'")
        return "\n".join(row[0] for row in cursor.fetchall())


def _migrate(target: str) -> None:
    # A fresh executor each time: the loader has to be rebuilt against the
    # recorder after every step.
    MigrationExecutor(connection).migrate([(APP, target)])


@pytest.fixture
def restore_migrations():
    """Leave the database at the migration head however the test ends."""
    yield
    _migrate(_head())


@pytest.mark.django_db(transaction=True)
def test_migrations_apply_to_a_table_that_already_has_rows(inbox_message, restore_migrations):
    sent_at = timezone.now() - timedelta(hours=1)
    reply = InboxReply.objects.create(inbox_message=inbox_message, body="delivered")
    InboxReply.objects.filter(pk=reply.pk).update(sent_at=sent_at)

    # Rewind past the lifecycle columns. Pre-0002 ``sent_at`` was
    # ``auto_now_add`` and NOT NULL, so a row that survives this rewind is by
    # definition the kind of row production had.
    _migrate(INITIAL)
    assert InboxReply.objects.count() == 1

    # The production path: add the indexed column and backfill over real rows.
    _migrate(_head())

    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    # ``created_at`` was re-added with a flat default (migration run time),
    # which is later than the real send; the backfill pulls it back.
    assert reply.created_at == sent_at

    # The index the deferred CREATE INDEX was failing to build. Pin the column,
    # not just the substring: 0002 also creates a varchar_pattern_ops index, and
    # matching "status" loosely would accept that one alone.
    assert "USING btree (status)" in _index_defs()


@pytest.mark.django_db(transaction=True)
def test_release_phase_writes_survive_the_schema_change(inbox_message, restore_migrations):
    """The old slug keeps serving through Heroku's release phase, and its
    INSERTs omit every column 0002 adds. 0003 puts the database defaults back
    so those writes do not hit a NOT NULL violation."""
    _migrate(_head())

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO inbox_reply (id, inbox_message_id, body, platform_reply_id, sent_at) "
            "VALUES (gen_random_uuid(), %s, 'from the old slug', '', now())",
            [inbox_message.pk],
        )

    old_slug_reply = InboxReply.objects.get(body="from the old slug")
    assert old_slug_reply.status == InboxReply.Status.DRAFT
    assert old_slug_reply.send_error == ""
    assert old_slug_reply.created_at is not None


@pytest.mark.django_db(transaction=True)
def test_migrations_can_be_rolled_back_with_a_draft_present(inbox_message, restore_migrations):
    """0002 reversed alone dies on ``sent_at`` NOT NULL once a draft exists;
    reversing the backfill first fills those in, so rollback stays available."""
    InboxReply.objects.create(inbox_message=inbox_message, body="a real draft")

    _migrate(INITIAL)

    assert InboxReply.objects.filter(body="a real draft").exists()


@pytest.mark.django_db
def test_backfill_marks_delivered_replies_sent(inbox_message):
    sent_at = timezone.now() - timedelta(hours=1)
    reply = InboxReply.objects.create(inbox_message=inbox_message, body="delivered")
    # Simulate a pre-0002 row: it predates the status column and was only ever
    # written post-send, so ``created_at`` is the column-add placeholder.
    InboxReply.objects.filter(pk=reply.pk).update(
        status=InboxReply.Status.DRAFT, sent_at=sent_at, created_at=timezone.now()
    )

    backfill._mark_existing_sent(global_apps, None)

    reply.refresh_from_db()
    assert reply.status == InboxReply.Status.SENT
    assert reply.created_at == sent_at


@pytest.mark.django_db
def test_backfill_leaves_unsent_replies_alone(inbox_message):
    """Staging applied the backfill inside 0002 and has since collected real
    drafts and failed sends; running it again as 0004 must not touch them."""
    draft = InboxReply.objects.create(inbox_message=inbox_message, body="not sent yet")
    failed = InboxReply.objects.create(inbox_message=inbox_message, body="bounced")
    InboxReply.objects.filter(pk=failed.pk).update(status=InboxReply.Status.FAILED, send_error="rate limited")

    backfill._mark_existing_sent(global_apps, None)

    draft.refresh_from_db()
    failed.refresh_from_db()
    assert draft.status == InboxReply.Status.DRAFT
    assert draft.sent_at is None
    # A FAILED reply stays retryable — services._SENDABLE_STATUSES keys off it.
    # Its NULL ``sent_at`` is the whole basis of the guard above, so pin it too:
    # if the failure path ever started stamping a send time, this backfill would
    # silently mark failed replies delivered.
    assert failed.status == InboxReply.Status.FAILED
    assert failed.sent_at is None
    assert failed.send_error == "rate limited"


@pytest.mark.django_db
def test_backfill_keeps_the_draft_time_of_a_reply_that_was_drafted_then_sent(inbox_message):
    drafted_at = timezone.now() - timedelta(hours=3)
    sent_at = timezone.now() - timedelta(hours=1)
    reply = InboxReply.objects.create(inbox_message=inbox_message, body="drafted, then sent")
    InboxReply.objects.filter(pk=reply.pk).update(status=InboxReply.Status.SENT, created_at=drafted_at, sent_at=sent_at)

    backfill._mark_existing_sent(global_apps, None)

    reply.refresh_from_db()
    assert reply.created_at == drafted_at


@pytest.mark.django_db(transaction=True)
def test_backfill_arriving_late_spares_rows_written_since_0002(inbox_message, restore_migrations):
    """Staging's path: it applied the backfill inside 0002 and has been taking
    traffic since, so the split backfill lands on a table holding real drafts."""
    _migrate(SCHEMA)

    sent_at = timezone.now() - timedelta(hours=1)
    drafted_at = timezone.now() - timedelta(hours=3)
    draft = InboxReply.objects.create(inbox_message=inbox_message, body="still a draft")
    failed = InboxReply.objects.create(inbox_message=inbox_message, body="bounced")
    InboxReply.objects.filter(pk=failed.pk).update(status=InboxReply.Status.FAILED, send_error="rate limited")
    delivered = InboxReply.objects.create(inbox_message=inbox_message, body="drafted, then sent")
    InboxReply.objects.filter(pk=delivered.pk).update(
        status=InboxReply.Status.SENT, created_at=drafted_at, sent_at=sent_at
    )

    _migrate(_head())

    draft.refresh_from_db()
    failed.refresh_from_db()
    delivered.refresh_from_db()
    assert draft.status == InboxReply.Status.DRAFT
    assert failed.status == InboxReply.Status.FAILED
    assert delivered.status == InboxReply.Status.SENT
    assert delivered.created_at == drafted_at
