"""One-shot Instagram (Direct) Meta App Review test-call command.

Fires the three API calls Meta requires verified test calls for:
  - instagram_business_content_publish  (POST /me/media + /me/media_publish)
  - instagram_business_manage_insights  (GET /{post_id}/insights + /me/insights)
  - instagram_business_manage_comments  (POST /{post_id}/comments)

Intended to be run live, on camera, against a connected ``instagram_login``
SocialAccount during App Review submission. Not wired into the worker, signals,
or any UI surface — invoke manually.

Usage:
    python manage.py instagram_review_test_calls \
        --account-id <uuid> \
        --image-url https://example.com/test.jpg
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

DEFAULT_CAPTION = "BrightBean App Review test post — please ignore."
DEFAULT_COMMENT = "BrightBean App Review test comment."


class Command(BaseCommand):
    help = "Fire the three Meta App Review test API calls (publish, insights, comment) against an Instagram (Direct) account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--account-id",
            required=True,
            help="UUID of the instagram_login SocialAccount to test against.",
        )
        parser.add_argument(
            "--image-url",
            required=True,
            help="Public HTTPS URL of an image Meta can fetch (JPEG/PNG). Localhost or short-TTL signed URLs will not work.",
        )
        parser.add_argument(
            "--caption",
            default=DEFAULT_CAPTION,
            help=f"Caption for the test post. Default: {DEFAULT_CAPTION!r}",
        )
        parser.add_argument(
            "--comment",
            default=DEFAULT_COMMENT,
            help=f"Comment to post on the new post. Default: {DEFAULT_COMMENT!r}",
        )
        parser.add_argument(
            "--skip-insights",
            action="store_true",
            help="Skip the insights call (use if instagram_business_manage_insights is already verified).",
        )
        parser.add_argument(
            "--skip-comment",
            action="store_true",
            help="Skip the comment call (use if instagram_business_manage_comments is already verified).",
        )

    def handle(self, *args, **opts):
        from apps.analytics.tasks import _resolve_provider  # mirror credential resolution
        from apps.social_accounts.models import SocialAccount
        from providers.types import PostType, PublishContent

        account_id = opts["account_id"]
        image_url = opts["image_url"]
        caption = opts["caption"]
        comment_text = opts["comment"]

        try:
            account = SocialAccount.objects.get(id=account_id)
        except SocialAccount.DoesNotExist as exc:
            raise CommandError(f"No SocialAccount with id={account_id!r}") from exc

        if account.platform != "instagram_login":
            raise CommandError(
                f"Account {account_id} is platform={account.platform!r}, but this command only operates on "
                f"'instagram_login' (the Instagram Direct connector).",
            )

        if account.connection_status != SocialAccount.ConnectionStatus.CONNECTED:
            self.stdout.write(
                self.style.WARNING(
                    f"Warning: account is in connection_status={account.connection_status!r} (not CONNECTED). "
                    f"Calls may fail. Continue anyway? Aborting if not. Reconnect first."
                )
            )
            raise CommandError("Account is not in CONNECTED status. Reconnect via /social-accounts/connect/ first.")

        self.stdout.write(f"Running App Review test calls for {account.account_name} (@{account.account_handle})…\n")

        provider = _resolve_provider(account)
        token = account.oauth_access_token

        # ------------------------------------------------------------------
        # 1. instagram_business_content_publish — publish_post()
        # ------------------------------------------------------------------
        self.stdout.write("  • Publishing test image (this may take 3–8 seconds while Meta fetches the URL)…")
        content = PublishContent(
            text=caption,
            media_urls=[image_url],
            post_type=PostType.IMAGE,
        )
        try:
            result = provider.publish_post(token, content)
        except Exception as exc:
            raise CommandError(f"publish_post failed: {exc}") from exc
        media_id = result.platform_post_id
        permalink = result.url or f"https://www.instagram.com/p/{media_id}/"
        self.stdout.write(
            self.style.SUCCESS(f"  ✓ instagram_business_content_publish — media_id={media_id}  permalink={permalink}")
        )

        # ------------------------------------------------------------------
        # 2. instagram_business_manage_insights — get_post_metrics() + get_account_metrics()
        # ------------------------------------------------------------------
        if opts["skip_insights"]:
            self.stdout.write("  - skipping insights call (--skip-insights)")
        else:
            self.stdout.write("  • Reading insights for the new post + account…")
            try:
                post_metrics = provider.get_post_metrics(token, media_id)
            except Exception as exc:
                raise CommandError(f"get_post_metrics failed: {exc}") from exc

            try:
                now = timezone.now()
                date_range = (now - timedelta(days=1), now)
                account_metrics = provider.get_account_metrics(token, date_range)
            except Exception as exc:
                raise CommandError(f"get_account_metrics failed: {exc}") from exc

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ instagram_business_manage_insights — "
                    f"post(reach={post_metrics.reach}, views={post_metrics.impressions}, "
                    f"likes={post_metrics.likes}, comments={post_metrics.comments}, saves={post_metrics.saves}); "
                    f"account(followers={account_metrics.followers}, reach={account_metrics.reach})"
                )
            )

        # ------------------------------------------------------------------
        # 3. instagram_business_manage_comments — publish_comment()
        # ------------------------------------------------------------------
        if opts["skip_comment"]:
            self.stdout.write("  - skipping comment call (--skip-comment)")
        else:
            self.stdout.write("  • Posting a comment on the new post…")
            try:
                comment_result = provider.publish_comment(token, media_id, comment_text)
            except Exception as exc:
                raise CommandError(f"publish_comment failed: {exc}") from exc
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ instagram_business_manage_comments — comment_id={comment_result.platform_comment_id}"
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done. All requested test calls succeeded."))
        self.stdout.write(
            "Check the Meta App Review dashboard — the touched permissions should flip to 'API call verified' "
            "within a minute or two."
        )
        self.stdout.write(f"You may want to delete the test post manually from Instagram: {permalink}")
