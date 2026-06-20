"""Reset queue assignments by removing terminal posts and recalculating slots."""

from django.core.management.base import BaseCommand, CommandError

from apps.calendar.models import Queue
from apps.calendar.services import assign_queue_slots, cleanup_terminal_queue_entries


class Command(BaseCommand):
    help = "Remove published/failed posts from queues and recalculate next-slot assignments."

    def add_arguments(self, parser):
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument("--account-id", help="Reset queues for one social account.")
        scope.add_argument("--workspace-id", help="Reset queues for one workspace.")
        scope.add_argument("--all", action="store_true", dest="all_queues", help="Reset all active queues.")
        parser.add_argument("--dry-run", action="store_true", help="Report changes without modifying queues.")

    def handle(self, *args, **options):
        queues = Queue.objects.filter(is_active=True).select_related("social_account")
        if options["account_id"]:
            queues = queues.filter(social_account_id=options["account_id"])
        elif options["workspace_id"]:
            queues = queues.filter(workspace_id=options["workspace_id"])
        elif not options["all_queues"]:
            raise CommandError("Choose --account-id, --workspace-id, or --all.")

        queues = list(queues.order_by("workspace_id", "social_account_id", "name"))
        if not queues:
            raise CommandError("No active queues matched the selected scope.")

        removed_entries = 0
        cleared_schedules = 0
        cleaned_account_ids = set()
        for queue in queues:
            if queue.social_account_id not in cleaned_account_ids:
                result = cleanup_terminal_queue_entries(
                    social_account=queue.social_account,
                    dry_run=options["dry_run"],
                )
                removed_entries += result["removed_entries"]
                cleared_schedules += result["cleared_schedules"]
                cleaned_account_ids.add(queue.social_account_id)
            if not options["dry_run"]:
                assign_queue_slots(queue)

        mode = "Would reset" if options["dry_run"] else "Reset"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} {len(queues)} queue(s): "
                f"{removed_entries} terminal queue entry(s), "
                f"{cleared_schedules} terminal schedule(s)."
            )
        )
