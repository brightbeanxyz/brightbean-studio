"""Backfill the ``InboxReply`` lifecycle columns added in ``0002``.

Split out of ``0002`` rather than merged into it, and not for tidiness:
``0002`` adds ``status`` with ``db_index=True``, and Django does not emit
that ``CREATE INDEX`` inline — ``schema_editor.add_field()`` appends it to
``deferred_sql``, which is flushed in the schema editor's ``__exit__``,
i.e. *after* every operation in the migration has run. All operations
share one editor and one transaction, so a ``RunPython`` sitting at the
bottom of ``0002`` actually executed *before* the index was built.

That is fatal on Postgres with real data. Django creates FK constraints
as ``DEFERRABLE INITIALLY DEFERRED``, so the backfill's ``UPDATE``s left
RI trigger events queued on ``inbox_reply`` until COMMIT, and Postgres
refuses to index a relation in that state::

    cannot CREATE INDEX "inbox_reply" because it has pending trigger events

An empty table hid it — 0 rows updated queues nothing — so this only
ever surfaced against production data. As its own migration the backfill
gets its own transaction: the index is built and committed by ``0002``
before a single row is touched.
"""

from django.db import migrations
from django.db.models import F
from django.db.models.functions import Least


def _mark_existing_sent(apps, schema_editor):
    InboxReply = apps.get_model("inbox", "InboxReply")
    # Pre-0002 rows were only ever written post-send, so ``sent_at`` was
    # ``auto_now_add`` and non-null on every one of them: "has a sent_at" is
    # exactly "existed before the lifecycle columns". Guarding on it also
    # makes this safe to run *late*, on a database that already applied the
    # backfill inside 0002 and has since collected genuine drafts (sent_at
    # NULL) and failed sends (sent_at NULL too — services.py only stamps it
    # on success, and a FAILED reply has to stay retryable).
    #
    # ``created_at`` got a flat default at column-add time, so it sorts every
    # historical reply as if it were written during the deploy; LEAST pulls it
    # back to the real send time for exactly those placeholder rows and leaves
    # a reply that was genuinely drafted before it was sent (created_at <=
    # sent_at) untouched. Doing both columns in one statement rewrites each
    # row once instead of twice.
    InboxReply.objects.filter(sent_at__isnull=False).update(
        status="sent", created_at=Least(F("created_at"), F("sent_at"))
    )


def _restore_sent_at(apps, schema_editor):
    """Give every unsent reply a ``sent_at`` so ``0002`` can be reversed.

    Reversing ``0002`` runs ``ALTER COLUMN "sent_at" SET NOT NULL`` without
    filling existing NULLs, so a rollback fails with ``column "sent_at" of
    relation "inbox_reply" contains null values`` the moment one real draft
    exists. Reversing this migration first clears that.

    Lossy by nature, and unavoidably so: the pre-0002 schema had nowhere to
    record that a reply was never sent, so a rolled-back draft becomes
    indistinguishable from a delivered one. Nothing is deleted — the body
    survives — but do not treat a rollback as round-trippable.
    """
    InboxReply = apps.get_model("inbox", "InboxReply")
    InboxReply.objects.filter(sent_at__isnull=True).update(sent_at=F("created_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("inbox", "0003_inboxreply_column_defaults"),
    ]

    operations = [
        migrations.RunPython(_mark_existing_sent, _restore_sent_at, elidable=True),
    ]
