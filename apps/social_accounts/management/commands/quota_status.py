"""Show which platform API budgets are currently spent.

When an account stops syncing there are two very different explanations, and
from the outside they look identical: the grant is broken and needs a
reconnect, or the platform's daily budget is gone and nothing is wrong with the
account at all. Telling a user to reconnect in the second case is worse than
useless — it mints a fresh token, and the sync resumes spending a budget that
is already empty.

This answers which one it is::

    python manage.py quota_status
    python manage.py quota_status --all      # include windows that have passed

Read-only.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.analytics.models import ProviderQuotaBlock


class Command(BaseCommand):
    help = "List platform API quota blocks currently in effect."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Also show blocks whose window has already passed.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        blocks = ProviderQuotaBlock.objects.all().order_by("platform", "quota_scope")
        if not options["all"]:
            blocks = blocks.filter(blocked_until__gt=now)

        rows = list(blocks)
        if not rows:
            self.stdout.write(self.style.SUCCESS("No quota blocks in effect — every platform budget is available."))
            return

        for block in rows:
            remaining = block.blocked_until - now
            expired = remaining.total_seconds() <= 0
            # Whole minutes: the windows that matter here are hours long, and a
            # seconds figure in the output reads as more precision than the
            # platform's own reset boundary actually gives us.
            minutes = int(abs(remaining).total_seconds() // 60)
            when = f"{minutes // 60}h{minutes % 60:02d}m"

            scope = block.quota_scope or "(single budget)"
            headline = f"{block.platform} [{scope}] credential {block.credential_key}"
            if expired:
                self.stdout.write(f"  {headline}: expired {when} ago")
                continue

            self.stdout.write(
                self.style.WARNING(
                    f"  {headline}: blocked for another {when} (until {block.blocked_until:%Y-%m-%d %H:%M} UTC)"
                )
            )
            if block.reason:
                self.stdout.write(f"      {block.reason}")

        if not options["all"]:
            self.stdout.write("")
            self.stdout.write(
                "Accounts on these platforms are not broken — their budget is spent. Pass --all for history."
            )
