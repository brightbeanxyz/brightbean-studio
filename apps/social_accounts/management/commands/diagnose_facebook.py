"""Diagnose why a connected Facebook Page is not delivering comments.

Two Facebook features fail for configuration reasons that look identical from
inside the app: a first comment that never appears, and Page comments that never
reach the inbox. Both come down to a permission that was never granted or a
webhook that was never wired up, and neither leaves a trace in the database.
This command asks Meta directly and prints the answer.

    python manage.py diagnose_facebook --workspace <uuid>
    python manage.py diagnose_facebook --account-id <uuid> --json
    python manage.py diagnose_facebook --account-id <uuid> --subscribe

Read-only unless --subscribe (repairs the Page subscription) or --test-comment
(posts a real comment on the newest post) is passed.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.social_accounts.models import SocialAccount

# The permissions whose absence explains a specific broken feature. Reporting
# "missing pages_manage_engagement" is useless on its own; reporting what stops
# working is what makes this command worth running.
CONSEQUENCE_BY_SCOPE = {
    "pages_manage_engagement": "first comments and inbox replies cannot be posted",
    "pages_read_user_content": "comments on the Page's posts cannot be read",
    "pages_read_engagement": "post metrics and comment counts are unavailable",
    "pages_messaging": "Messenger DMs cannot be read or answered",
    "pages_manage_metadata": "webhook subscriptions cannot be created",
    "pages_manage_posts": "posts cannot be published",
}


class Command(BaseCommand):
    help = "Report why a connected Facebook Page is missing comments (permissions, webhooks, readability)."

    def add_arguments(self, parser):
        parser.add_argument("--account-id", help="Only this SocialAccount UUID.")
        parser.add_argument("--workspace", help="Only accounts in this workspace UUID.")
        parser.add_argument(
            "--subscribe",
            action="store_true",
            help="Repair a missing Page webhook subscription in place.",
        )
        parser.add_argument(
            "--test-comment",
            metavar="TEXT",
            help="Post this text as a real comment on the newest post (writes to the live Page).",
        )
        parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    def handle(self, *args, **options):
        accounts = SocialAccount.objects.filter(
            platform="facebook",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        ).select_related("workspace")

        if options["account_id"]:
            accounts = accounts.filter(id=options["account_id"])
        if options["workspace"]:
            accounts = accounts.filter(workspace_id=options["workspace"])

        accounts = list(accounts.order_by("account_name"))
        if not accounts:
            raise CommandError("No connected Facebook accounts matched.")

        reports = [self._diagnose(account, options) for account in accounts]

        if options["json"]:
            import json

            self.stdout.write(json.dumps(reports, indent=2, default=str))
        else:
            for report in reports:
                self._print(report)

        # Non-zero exit so this can be used as a probe.
        if any(check["ok"] is False for report in reports for check in report["checks"]):
            raise CommandError("One or more checks failed (see above).")

    # ------------------------------------------------------------------

    def _diagnose(self, account, options) -> dict:
        report: dict = {
            "account": f"{account.account_name} ({account.id})",
            "page_id": account.account_platform_id,
            "checks": [],
        }

        def check(name, ok, detail):
            report["checks"].append({"name": name, "ok": ok, "detail": detail})

        self._check_local_state(account, check)

        try:
            from apps.social_accounts.views import _apply_analytics_scope_flag, _get_provider_for_platform

            provider = _get_provider_for_platform("facebook", account.workspace.organization_id)
            # Mirror what the OAuth flow does, or required_scopes reports
            # read_insights as expected on a deployment where analytics is
            # deliberately off — and a healthy token gets reported as broken.
            _apply_analytics_scope_flag(provider, "facebook")
        except Exception as exc:
            check("provider", False, f"could not build the Facebook provider: {exc}")
            return report

        # Each check is isolated: a 403 on permissions must not hide the
        # webhook answer, which is usually the one that matters.
        self._check_permissions(account, provider, check)
        self._check_app_registration(provider, check)
        self._check_subscription(account, provider, check, subscribe=options["subscribe"])
        newest_post_id = self._check_comment_readability(account, provider, check)

        if options["test_comment"]:
            self._check_comment_write(account, provider, check, newest_post_id, options["test_comment"])

        return report

    def _check_local_state(self, account, check):
        from apps.inbox.models import InboxMessage

        comments = InboxMessage.objects.filter(
            social_account=account,
            message_type=InboxMessage.MessageType.COMMENT,
        )
        newest = comments.order_by("-received_at").values_list("received_at", flat=True).first()
        recent = comments.filter(received_at__gte=timezone.now() - timedelta(days=30)).count()

        check(
            "inbox history",
            None,
            f"{recent} comment(s) in the last 30 days; newest {newest or 'never'}",
        )
        check(
            "webhook subscription (local record)",
            account.webhooks_active is not False,
            account.webhook_error or f"webhooks_active={account.webhooks_active}",
        )
        check(
            "FACEBOOK_WEBHOOK_VERIFY_TOKEN",
            bool(settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN),
            "set" if settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN else "not set — Meta cannot verify the callback URL",
        )
        check("token expiry", None, str(account.token_expires_at or "no expiry recorded"))

    def _check_permissions(self, account, provider, check):
        try:
            data = provider.debug_token(account.oauth_access_token)
        except Exception as exc:
            check("granted permissions", False, f"could not inspect the token: {exc}")
            return

        granted = set(data.get("scopes") or [])
        missing = [s for s in provider.required_scopes if s not in granted]

        check(
            "token validity",
            bool(data.get("is_valid")),
            f"type={data.get('type', '?')} expires_at={data.get('expires_at', 'never')} "
            f"data_access_expires_at={data.get('data_access_expires_at', '?')}",
        )
        if missing:
            detail = "; ".join(f"{scope} → {CONSEQUENCE_BY_SCOPE.get(scope, 'unknown impact')}" for scope in missing)
            check("granted permissions", False, f"missing: {detail}")
        else:
            check("granted permissions", True, f"all {len(provider.required_scopes)} required scopes granted")

    def _check_app_registration(self, provider, check):
        """Does the app itself have a callback URL registered for Pages?

        The half of Meta's setup that nothing in this codebase can create, and
        the one that fails invisibly: without it, every per-Page subscription
        reports healthy and Meta still never delivers a single event.
        """
        from providers.facebook import FACEBOOK_WEBHOOK_FIELDS

        try:
            subscriptions = provider.get_app_subscriptions()
        except Exception as exc:
            check("app webhook registration", False, f"could not read the app's subscriptions: {exc}")
            return

        page_sub = next((s for s in subscriptions if s.get("object") == "page"), None)
        expected = f"{getattr(settings, 'APP_URL', '').rstrip('/')}/webhooks/facebook/"

        if page_sub is None:
            check(
                "app webhook registration",
                False,
                "the app has NO callback URL registered for the 'page' object. Meta will never deliver "
                f"Page events no matter how many Pages are subscribed. Register {expected} under "
                "App Dashboard → Webhooks → Page, then subscribe the 'feed' field.",
            )
            return

        callback = page_sub.get("callback_url", "")
        fields = {f.get("name") if isinstance(f, dict) else f for f in (page_sub.get("fields") or [])}
        missing = [f for f in FACEBOOK_WEBHOOK_FIELDS if f not in fields]
        problems = []
        if not page_sub.get("active", True):
            problems.append("the registration is INACTIVE (Meta disables it after repeated delivery failures)")
        if expected and callback.rstrip("/") != expected.rstrip("/"):
            problems.append(f"callback is {callback or 'unset'}, expected {expected}")
        if missing:
            problems.append(f"missing field(s) {missing} — 'feed' is what carries comments")

        check(
            "app webhook registration",
            not problems,
            "; ".join(problems) if problems else f"page → {callback} ({sorted(fields)})",
        )

    def _check_subscription(self, account, provider, check, *, subscribe: bool):
        from apps.social_accounts.views import _webhook_target
        from providers.facebook import FACEBOOK_WEBHOOK_FIELDS

        target = _webhook_target(account)
        try:
            subscriptions = provider.get_webhook_subscriptions(account.oauth_access_token, target)
        except Exception as exc:
            check("webhook subscription (Meta)", False, f"could not read subscribed_apps: {exc}")
            return

        app_id = str(provider.credentials.get("client_id", ""))
        ours = next((s for s in subscriptions if str(s.get("id")) == app_id), None)

        if ours is None:
            check(
                "webhook subscription (Meta)",
                False,
                f"this app (id {app_id}) is not subscribed to Page {target}. "
                f"Re-run with --subscribe, or `manage.py subscribe_webhooks --platform facebook --retry-failed`.",
            )
        else:
            fields = set(ours.get("subscribed_fields") or [])
            missing = [f for f in FACEBOOK_WEBHOOK_FIELDS if f not in fields]
            check(
                "webhook subscription (Meta)",
                not missing,
                f"subscribed to {sorted(fields) or 'nothing'}"
                + (f"; missing {missing} — 'feed' is what carries comments" if missing else ""),
            )

        if subscribe:
            from apps.social_accounts.views import _subscribe_account_webhooks

            ok = _subscribe_account_webhooks(account)
            check("webhook subscription (repair)", ok, "subscribed" if ok else "the platform refused")

    def _check_comment_readability(self, account, provider, check) -> str:
        """Read the Page feed the way the inbox poll does. Returns the newest post id."""
        from providers.facebook import BASE_URL, FACEBOOK_FEED_SCAN_LIMIT

        # Scan the same window the inbox poll uses, not just the newest few —
        # "0 comments" is only meaningful if we looked everywhere the poll does.
        try:
            resp = provider._request(
                "GET",
                f"{BASE_URL}/{account.account_platform_id}/feed",
                access_token=account.oauth_access_token,
                params={
                    "fields": ("id,created_time,permalink_url,comments.limit(25){id,message,from,created_time}"),
                    "limit": FACEBOOK_FEED_SCAN_LIMIT,
                },
            )
            posts = resp.json().get("data", [])
        except Exception as exc:
            check("read comments", False, f"GET /feed failed: {exc}")
            return ""

        comments = [c for post in posts for c in (post.get("comments") or {}).get("data", [])]
        authored = sum(1 for c in comments if c.get("from"))

        check(
            "read comments",
            True,
            f"{len(posts)} post(s) scanned, {len(comments)} comment(s) visible"
            + (
                ""
                if not comments or authored
                else " — every comment is missing its author, which usually means pages_read_user_content is absent"
            ),
        )

        # Per-post detail: a comment the user swears they left, on a post the
        # scan can see with zero comments, is a very different problem from a
        # comment sitting on a post older than the window.
        for post in posts:
            post_comments = (post.get("comments") or {}).get("data", [])
            if not post_comments:
                continue
            check(
                f"comments on {post.get('id')}",
                None,
                f"{post.get('created_time', '?')} → "
                + "; ".join(
                    f"{(c.get('from') or {}).get('name', 'unknown')}: {(c.get('message') or '')[:40]}"
                    for c in post_comments
                ),
            )

        return str(posts[0].get("id", "")) if posts else ""

    def _check_comment_write(self, account, provider, check, post_id: str, text: str):
        if not post_id:
            check("post a comment", False, "no recent post to comment on")
            return
        try:
            result = provider.publish_comment(account.oauth_access_token, post_id, text)
        except Exception as exc:
            check("post a comment", False, f"{exc}")
            return
        check("post a comment", True, f"created comment {result.platform_comment_id}")

    # ------------------------------------------------------------------

    def _print(self, report):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"{report['account']} — page {report['page_id']}"))
        for item in report["checks"]:
            if item["ok"] is True:
                marker = self.style.SUCCESS("  PASS")
            elif item["ok"] is False:
                marker = self.style.ERROR("  FAIL")
            else:
                marker = "  INFO"
            self.stdout.write(f"{marker}  {item['name']}: {item['detail']}")
