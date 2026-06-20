"""Normalise QueueEntry positions to be 0-indexed per queue.

Before the gap-aware scheduling change, add_to_queue computed:
    position = (max_pos or 0) + 1

This placed the very first entry at position 1, making all legacy queues
1-indexed (1, 2, 3 …).  assign_queue_slots now uses position as a direct
slot index, so a queue starting at 1 leaves slot 0 permanently empty and
shifts every queued post one slot later than expected.

For each queue, shift all positions down by the queue's minimum position so
the sequence always starts at 0.  Queues that already start at 0 (e.g.
created after the main change) or are empty are left untouched.
"""

from django.db import migrations


def normalise_positions(apps, schema_editor):
    QueueEntry = apps.get_model("calendar", "QueueEntry")
    Queue = apps.get_model("calendar", "Queue")

    for queue in Queue.objects.all():
        entries = list(QueueEntry.objects.filter(queue=queue).order_by("position"))
        if not entries:
            continue
        min_pos = entries[0].position
        if min_pos == 0:
            continue
        for entry in entries:
            entry.position -= min_pos
        QueueEntry.objects.bulk_update(entries, ["position"])


def reverse_normalise(apps, schema_editor):
    # Reversing would require knowing the original offset per queue, which we
    # no longer have.  Treat as a no-op — positions remain normalised.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("calendar", "0005_alter_customcalendarevent_color"),
    ]

    operations = [
        migrations.RunPython(normalise_positions, reverse_normalise),
    ]
