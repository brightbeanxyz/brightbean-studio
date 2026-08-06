"""Subscribe already-connected accounts to their platform webhooks.

Subscription happens when an account is connected, so every account connected
before that code existed is still unsubscribed — its inbox silently misses
comments and mentions, which have no polling fallback. Run this once after
deploying, and again whenever you want to repair accounts whose subscription
was refused.

    python manage.py subscribe_webhooks --dry-run
    python manage.py subscribe_webhooks
    python manage.py subscribe_webhooks --platform facebook --retry-failed
"""

from django.core.management.base import BaseCommand

from apps.social_accounts.models import SocialAccount


class Command(BaseCommand):
    help = "Subscribe connected accounts to their platform webhooks (comments, mentions, messages)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--platform",
            help="Only this platform (e.g. facebook, instagram, instagram_login).",
        )
        parser.add_argument(
            "--workspace",
            help="Only accounts in this workspace ID.",
        )
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Include accounts whose last subscription attempt failed.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be subscribed without calling the platform.",
        )

    def handle(self, *args, **options):
        from apps.social_accounts.views import _subscribe_account_webhooks, _supports_webhooks, _webhook_target

        accounts = SocialAccount.objects.filter(
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        ).select_related("workspace")

        if options["platform"]:
            accounts = accounts.filter(platform=options["platform"])
        if options["workspace"]:
            accounts = accounts.filter(workspace_id=options["workspace"])
        if not options["retry_failed"]:
            # Already-subscribed accounts are skipped; a previous failure is
            # only retried when explicitly asked for, so a broken credential
            # does not get hammered on every run.
            accounts = accounts.filter(webhooks_active__isnull=True)

        subscribed = skipped = failed = 0

        for account in accounts.order_by("platform", "account_name"):
            label = f"{account.platform}/{account.account_name} ({account.id})"

            try:
                from apps.social_accounts.views import _get_provider_for_platform

                provider = _get_provider_for_platform(account.platform, account.workspace.organization_id)
            except Exception as exc:
                self.stderr.write(f"  ! {label}: could not build provider — {exc}")
                failed += 1
                continue

            if not _supports_webhooks(provider):
                skipped += 1
                continue

            if not account.oauth_access_token:
                self.stderr.write(f"  ! {label}: no access token; reconnect required")
                failed += 1
                continue

            if options["dry_run"]:
                self.stdout.write(f"  would subscribe {label} -> {_webhook_target(account)}")
                subscribed += 1
                continue

            if _subscribe_account_webhooks(account):
                self.stdout.write(self.style.SUCCESS(f"  subscribed {label}"))
                subscribed += 1
            else:
                account.refresh_from_db()
                self.stderr.write(f"  ! {label}: {account.webhook_error or 'subscription refused'}")
                failed += 1

        verb = "would subscribe" if options["dry_run"] else "subscribed"
        self.stdout.write(f"\n{verb} {subscribed}, skipped {skipped} (no webhook support), failed {failed}.")
