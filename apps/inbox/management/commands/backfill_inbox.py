"""Management command to backfill historical inbox messages."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inbox.tasks import InboxSyncEngine
from apps.social_accounts.models import SocialAccount
from providers import get_provider


class Command(BaseCommand):
    help = "Backfill historical inbox messages for connected accounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to backfill (default: 7).",
        )
        parser.add_argument(
            "--platform",
            type=str,
            default=None,
            help="Only backfill a specific platform (e.g., youtube, linkedin, tiktok).",
        )
        parser.add_argument(
            "--account-id",
            type=str,
            default=None,
            help="Only backfill a specific account by UUID.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        platform_filter = options["platform"]
        account_id = options["account_id"]
        since = timezone.now() - timedelta(days=days)
        engine = InboxSyncEngine()

        accounts = SocialAccount.objects.filter(
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        ).select_related("workspace")

        if platform_filter:
            accounts = accounts.filter(platform=platform_filter)
        if account_id:
            accounts = accounts.filter(id=account_id)

        self.stdout.write(f"Backfilling {days} days of messages for {accounts.count()} account(s)...")

        from apps.publisher.engine import _resolve_publish_credentials

        for account in accounts:
            try:
                provider = get_provider(account.platform, _resolve_publish_credentials(account))
                messages = provider.get_messages(
                    access_token=account.oauth_access_token,
                    since=since,
                )
                count = 0
                for msg in messages:
                    # Backfill is explicit history seeding — never notify (the
                    # periodic sync alerts for genuinely new messages instead).
                    engine._upsert_message(account, msg, notify=False)
                    count += 1
                self.stdout.write(self.style.SUCCESS(f"  {account.platform}/{account.account_name}: {count} messages"))
            except NotImplementedError:
                self.stdout.write(f"  {account.platform}/{account.account_name}: skipped (not supported)")
            except Exception as e:
                self.stderr.write(f"  {account.platform}/{account.account_name}: ERROR - {e}")

        self.stdout.write(self.style.SUCCESS("Backfill complete."))
