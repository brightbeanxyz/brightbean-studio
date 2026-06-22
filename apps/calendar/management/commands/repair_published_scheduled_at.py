"""Repair published posts whose ``scheduled_at`` was dragged into the future.

A queue bug re-slotted already-published entries when a queue was added to or
reordered, pushing their ``scheduled_at`` onto a future posting slot. The
calendar places chips by ``scheduled_at``, so those posts showed up as
"published" up to a week ahead. This command resets the affected rows'
``scheduled_at`` back to their true ``published_at``.

The detection/repair logic lives in
``apps.calendar.services.repair_future_published_scheduled_at`` so the command
and any future caller never drift.

Usage:
    python manage.py repair_published_scheduled_at --dry-run
    python manage.py repair_published_scheduled_at
    python manage.py repair_published_scheduled_at --workspace <workspace-uuid>
"""

from django.core.management.base import BaseCommand

from apps.calendar.services import repair_future_published_scheduled_at


class Command(BaseCommand):
    help = "Reset scheduled_at for published posts pushed into the future by the queue re-slot bug."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report affected posts without writing any changes.",
        )
        parser.add_argument(
            "--workspace",
            default=None,
            help="Limit the repair to a single workspace UUID (default: all workspaces).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        workspace_id = options["workspace"]

        result = repair_future_published_scheduled_at(workspace_id=workspace_id, apply=not dry_run)
        rows = result["rows"]

        if not rows:
            self.stdout.write(self.style.SUCCESS("No affected posts found — nothing to repair."))
            return

        header = "Would repair" if dry_run else "Repaired"
        self.stdout.write(
            f"{header} {result['platform_post_count']} platform post(s) across {result['post_count']} post(s) "
            f"(+{result['queue_entry_count']} stale queue slot(s)):"
        )
        for row in rows:
            self.stdout.write(
                "  {platform:<18} {account:<24} {old} -> {new}  (post {post})".format(
                    platform=row["platform"],
                    account=(row["account"] or "")[:24],
                    old=row["old_scheduled_at"].isoformat(),
                    new=row["new_scheduled_at"].isoformat(),
                    post=row["post_id"],
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run — no changes written. Re-run without --dry-run to apply."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDone. Reset {result['platform_post_count']} platform post(s) "
                    f"and {result['queue_entry_count']} queue slot(s)."
                )
            )
