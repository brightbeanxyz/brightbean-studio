"""Facebook Graph API provider implementation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse

from .base import SocialProvider
from .exceptions import APIError, OAuthError, PublishError
from .meta_comments import parse_graph_time
from .meta_insights import fetch_insights_safe, parse_insights_response
from .meta_messaging import build_send_payload, resolve_recipient_id
from .types import (
    AccountMetrics,
    AccountProfile,
    AuthType,
    CommentResult,
    InboxMessage,
    MediaType,
    OAuthTokens,
    PostMetrics,
    PostType,
    PublishContent,
    PublishResult,
    RateLimitConfig,
    ReplyResult,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.facebook.com/v25.0"
OAUTH_URL = "https://www.facebook.com/v25.0/dialog/oauth"
TOKEN_URL = f"{BASE_URL}/oauth/access_token"
# Webhook fields we subscribe a connected Page to. ``feed`` carries comments on
# the Page's posts, ``mention`` carries mentions of the Page, ``messages``
# carries Messenger conversations. Webhooks are the low-latency route; the
# ``get_messages`` poll is the backstop that keeps comments arriving when the
# subscription is missing or Meta stops delivering.
FACEBOOK_WEBHOOK_FIELDS = ["feed", "mention", "messages"]
FACEBOOK_PAGE_INSIGHTS = [
    "page_media_view",
    "page_total_media_view_unique",
    "page_daily_follows_unique",
    "page_follows",
    "page_post_engagements",
]
FACEBOOK_POST_INSIGHTS = [
    "post_media_view",
    "post_total_media_view_unique",
    "post_clicks",
    "post_reactions_by_type_total",
]
FACEBOOK_POST_FIELDS = [
    "id",
    "message",
    "created_time",
    "permalink_url",
    "full_picture",
    "post_id",
    "shares",
    "comments.limit(0).summary(true)",
    "reactions.limit(0).summary(true)",
]

# Comment-poll bounds. The poll is a backstop for the ``feed`` webhook, so it
# trades completeness on very busy Pages for a predictable per-cycle cost: one
# feed call plus at most FACEBOOK_COMMENT_PAGE_LIMIT follow-ups per post.
FACEBOOK_FEED_SCAN_LIMIT = 25
FACEBOOK_COMMENTS_PER_POST = 50
FACEBOOK_COMMENT_PAGE_LIMIT = 4
# How far back the *post* scan reaches. Comments on posts older than this are
# only reachable via the webhook.
FACEBOOK_FEED_WINDOW_DAYS = 30
# Overlap applied to the caller's ``since``. The inbox passes the newest
# received_at across *all* message types for the account, so a DM that arrived
# after a comment would otherwise hide that comment forever. Re-fetching the
# overlap is free: _upsert_message only notifies on create.
FACEBOOK_COMMENT_LOOKBACK_HOURS = 24
FACEBOOK_COMMENT_FIELDS = "id,message,created_time,from,parent,permalink_url"

# Facebook caps the ``attached_media`` array on a single feed post. Larger sets
# must use the album-creation flow, which this provider does not implement.
FACEBOOK_MAX_ATTACHED_MEDIA = 10
# Extension heuristic for spotting video URLs, mirroring the per-item checks in
# the Instagram / Threads carousel providers.
VIDEO_URL_SUFFIXES = (".mp4", ".mov")


class FacebookProvider(SocialProvider):
    """Facebook Graph API v25.0 provider."""

    def __init__(self, credentials: dict | None = None):
        creds = dict(credentials or {})
        # Normalize: accept app_id/app_secret as aliases for client_id/client_secret
        if "app_id" in creds and "client_id" not in creds:
            creds["client_id"] = creds.pop("app_id")
        if "app_secret" in creds and "client_secret" not in creds:
            creds["client_secret"] = creds.pop("app_secret")
        super().__init__(creds)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "Facebook"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 63206

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.TEXT, PostType.IMAGE, PostType.VIDEO, PostType.LINK]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4, MediaType.MOV]

    @property
    def required_scopes(self) -> list[str]:
        scopes = [
            "business_management",
            "pages_show_list",
            # Required by publish_comment() — POST /{post_id}/comments is gated
            # behind pages_manage_engagement.
            "pages_manage_engagement",
            "pages_manage_posts",
            "pages_read_engagement",
            "pages_read_user_content",
            "pages_manage_metadata",
            "pages_messaging",
        ]
        if self.include_analytics_scopes:
            scopes.extend(self.analytics_only_scopes)
        return scopes

    @property
    def analytics_only_scopes(self) -> list[str]:
        # ``read_insights`` is required for page/post insights. Only requested
        # in OAuth when this platform's analytics is enabled.
        return ["read_insights"]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=4800,
            publish_per_day=4800,
            extra={"posts_per_24h_per_page": 4800},
        )

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.required_scopes),
            "response_type": "code",
        }
        return f"{OAUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
        resp = self._request(
            "POST",
            TOKEN_URL,
            params={
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
            },
        )
        data = resp.json()
        if "access_token" not in data:
            raise OAuthError(
                "Facebook token exchange failed",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            raw_response=data,
        )

    def refresh_token(self, short_lived_token: str) -> OAuthTokens:
        """Exchange a short-lived token for a long-lived token.

        Facebook does not use traditional refresh tokens. Instead, you
        exchange a short-lived user token for a long-lived one (valid ~60 days).
        """
        resp = self._request(
            "GET",
            f"{BASE_URL}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "fb_exchange_token": short_lived_token,
            },
        )
        data = resp.json()
        if "access_token" not in data:
            raise OAuthError(
                "Facebook long-lived token exchange failed",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            raw_response=data,
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        resp = self._request(
            "GET",
            f"{BASE_URL}/me",
            access_token=access_token,
            params={"fields": "id,name,picture"},
        )
        data = resp.json()
        avatar = None
        if "picture" in data and "data" in data["picture"]:
            avatar = data["picture"]["data"].get("url")
        return AccountProfile(
            platform_id=data["id"],
            name=data.get("name", ""),
            avatar_url=avatar,
            extra=data,
        )

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def get_user_pages(self, access_token: str) -> list[dict]:
        """Fetch the pages that the authenticated user manages.

        Returns a list of dicts each containing id, name, access_token,
        category, and picture.
        """
        resp = self._request(
            "GET",
            f"{BASE_URL}/me/accounts",
            access_token=access_token,
            params={"fields": "id,name,access_token,category,picture,followers_count"},
        )
        data = resp.json()
        if "error" in data:
            logger.error("Facebook /me/accounts error: %s", data["error"])
            raise APIError(
                f"Failed to fetch pages: {data['error'].get('message', 'Unknown error')}",
                platform=self.platform_name,
                raw_response=data,
            )
        logger.debug("Facebook /me/accounts returned %d pages", len(data.get("data", [])))
        pages: list[dict] = []
        for page in data.get("data", []):
            picture_url = None
            if "picture" in page and "data" in page["picture"]:
                picture_url = page["picture"]["data"].get("url")
            pages.append(
                {
                    "id": page["id"],
                    "name": page.get("name", ""),
                    "access_token": page.get("access_token", ""),
                    "category": page.get("category", ""),
                    "picture": picture_url,
                    "followers_count": page.get("followers_count", 0),
                }
            )
        return pages

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        page_id = content.extra.get("page_id")
        if not page_id:
            raise PublishError(
                "page_id is required in content.extra for Facebook publishing",
                platform=self.platform_name,
            )

        if content.post_type == PostType.IMAGE and content.media_urls:
            return self._publish_photo(access_token, page_id, content)
        if content.post_type == PostType.VIDEO and content.media_urls:
            return self._publish_video(access_token, page_id, content)
        return self._publish_text_or_link(access_token, page_id, content)

    def _publish_text_or_link(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        payload: dict = {"message": content.text}
        if content.link_url:
            payload["link"] = content.link_url
        resp = self._request(
            "POST",
            f"{BASE_URL}/{page_id}/feed",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        post_id = self._stored_post_id(data["id"])
        return PublishResult(
            platform_post_id=post_id,
            url=f"https://www.facebook.com/{data['id']}",
            extra=data,
        )

    def _publish_photo(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        if len(content.media_urls) > 1:
            return self._publish_multi_photo(access_token, page_id, content)

        payload: dict = {"url": content.media_urls[0]}
        if content.text:
            payload["message"] = content.text
        resp = self._request(
            "POST",
            f"{BASE_URL}/{page_id}/photos",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        graph_post_id = data.get("post_id", data["id"])
        post_id = self._stored_post_id(graph_post_id)
        return PublishResult(
            platform_post_id=post_id,
            url=f"https://www.facebook.com/{graph_post_id}",
            extra=data,
        )

    def _publish_multi_photo(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        urls = content.media_urls

        # Pre-staging guards: fail before any network call so we never leave
        # orphaned unpublished photos behind for an obviously invalid request.
        if len(urls) > FACEBOOK_MAX_ATTACHED_MEDIA:
            raise PublishError(
                f"Facebook multi-photo posts support at most {FACEBOOK_MAX_ATTACHED_MEDIA} photos (got {len(urls)})",
                platform=self.platform_name,
            )
        if any(self._is_video_url(url) for url in urls):
            raise PublishError(
                "Facebook multi-photo posts support images only; post videos separately",
                platform=self.platform_name,
            )

        photo_ids: list[str] = []
        try:
            for url in urls:
                data = self._request(
                    "POST",
                    f"{BASE_URL}/{page_id}/photos",
                    access_token=access_token,
                    json={"url": url, "published": False},
                ).json()
                photo_id = data.get("id")
                if not photo_id:
                    raise PublishError(
                        "Failed to stage Facebook photo for multi-photo post",
                        platform=self.platform_name,
                        raw_response=data,
                    )
                photo_ids.append(photo_id)

            payload: dict = {
                "attached_media": [{"media_fbid": photo_id} for photo_id in photo_ids],
            }
            if content.text:
                payload["message"] = content.text

            data = self._request(
                "POST",
                f"{BASE_URL}/{page_id}/feed",
                access_token=access_token,
                json=payload,
            ).json()
            graph_post_id = data.get("id")
            if not graph_post_id:
                raise PublishError(
                    "Failed to publish Facebook multi-photo post",
                    platform=self.platform_name,
                    raw_response=data,
                )
        except Exception:
            # Best-effort: remove any photos already staged as unpublished so a
            # partial failure (or a retry by the publisher) doesn't accumulate
            # orphaned media on the page.
            self._delete_staged_photos(access_token, photo_ids)
            raise

        return PublishResult(
            platform_post_id=self._stored_post_id(graph_post_id),
            url=f"https://www.facebook.com/{graph_post_id}",
            extra={**data, "photo_ids": photo_ids},
        )

    @staticmethod
    def _is_video_url(url: str) -> bool:
        """Heuristically detect a video URL by file extension.

        Uses the URL path only so presigned query strings (R2/S3) don't defeat
        the check.
        """
        return urlparse(url).path.lower().endswith(VIDEO_URL_SUFFIXES)

    def _delete_staged_photos(self, access_token: str, photo_ids: list[str]) -> None:
        """Best-effort cleanup of unpublished photos staged for a multi-photo post.

        Swallows errors so cleanup never masks the original publish failure.
        """
        for photo_id in photo_ids:
            try:
                self._request("DELETE", f"{BASE_URL}/{photo_id}", access_token=access_token)
            except Exception:
                logger.warning("Failed to clean up staged Facebook photo %s", photo_id)

    def _publish_video(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        payload: dict = {"file_url": content.media_urls[0]}
        if content.text:
            payload["description"] = content.text
        resp = self._request(
            "POST",
            f"{BASE_URL}/{page_id}/videos",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        video_id = data["id"]
        # Resolve the feed post id + permalink so analytics target the page post
        # and the stored URL is shareable. Best-effort: video processing is async,
        # so post_id may not be ready yet — fall back to the bare video id.
        video_fields: dict = {}
        try:
            video_fields = self._request(
                "GET",
                f"{BASE_URL}/{video_id}",
                access_token=access_token,
                params={"fields": "post_id,permalink_url"},
            ).json()
        except Exception as exc:
            # Best-effort metadata that runs AFTER the video has already
            # published: nothing here may propagate, or the publish engine would
            # schedule a retry and double-post the video (e.g. a malformed 2xx
            # body making .json() raise). Catch broadly; fall back to video_id.
            logger.debug("Facebook video %s post_id unavailable: %s", video_id, exc)

        graph_post_id = video_fields.get("post_id") or video_id
        post_id = self._stored_post_id(graph_post_id)
        url = video_fields.get("permalink_url") or f"https://www.facebook.com/{graph_post_id}"
        return PublishResult(
            platform_post_id=post_id,
            url=url,
            extra={**data, **video_fields, "video_id": video_id},
        )

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def _comment_target_ids(self, post_id: str) -> list[str]:
        """Graph nodes to try, in order, when commenting on a stored post id.

        ``_publish_video`` stores the bare VIDEO id whenever the feed post_id
        lookup fails (video processing is async). Page-scoping that id
        fabricates ``{page_id}_{video_id}``, which is not a real object — but
        the raw video node does accept the comments edge, so it is the fallback.
        """
        post_id = str(post_id or "")
        candidates = [self._page_scoped_post_id(post_id), post_id]
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        first_error: APIError | None = None
        for target in self._comment_target_ids(post_id):
            try:
                resp = self._request(
                    "POST",
                    f"{BASE_URL}/{target}/comments",
                    access_token=access_token,
                    json={"message": text},
                )
            except APIError as exc:
                # Only a "no such object" answer earns a second attempt. On a
                # 5xx the comment may well have been created server-side, and
                # posting again would double-comment on a live Page.
                if exc.status_code not in (400, 404):
                    raise
                first_error = first_error or exc
                logger.info("Facebook comment target %s rejected; trying next candidate", target)
                continue
            data = resp.json()
            return CommentResult(platform_comment_id=data["id"], extra={**data, "post_id": target})

        raise first_error or APIError(
            f"No usable Facebook comment target for post {post_id}",
            platform=self.platform_name,
        )

    def find_own_comment(self, access_token: str, post_id: str, text: str) -> str | None:
        """Find a comment the Page already posted on ``post_id`` with this text.

        Called before retrying a first comment whose previous attempt failed
        ambiguously. Errs toward reporting a match: a false positive costs one
        skipped comment, a false negative posts a duplicate on a live Page.
        """
        page_id = str(self.credentials.get("page_id") or "")

        for target in self._comment_target_ids(post_id):
            try:
                resp = self._request(
                    "GET",
                    f"{BASE_URL}/{target}/comments",
                    access_token=access_token,
                    params={"fields": "id,message,from", "limit": FACEBOOK_COMMENTS_PER_POST},
                )
            except APIError as exc:
                # Only "no such object" means this candidate target was the
                # wrong guess and the next one deserves a try. Any other failure
                # leaves the answer unknown, and returning None for it tells the
                # caller it is safe to post again — the duplicate this whole
                # lookup exists to prevent.
                if exc.status_code not in (400, 404):
                    raise
                continue

            for comment in resp.json().get("data", []):
                author_id = str((comment.get("from") or {}).get("id") or "")
                # Only skip on a *known* mismatch — an unreadable author must
                # not turn into "not ours, go ahead and post again".
                if page_id and author_id and author_id != page_id:
                    continue
                if (comment.get("message") or "") == text:
                    return str(comment.get("id") or "")
        return None

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        fields, insight_candidates = self._resolve_post_fields(access_token, post_id)
        values, errors, insight_post_id = self._get_post_insights(access_token, insight_candidates)

        reactions = values.get("post_reactions_by_type_total", {})
        if isinstance(reactions, dict) and reactions:
            reactions_total = sum(reactions.values())
        else:
            reactions_total = fields.get("reactions", {}).get("summary", {}).get("total_count", 0)

        comments = self._summary_total(fields, "comments")
        shares = self._share_count(fields)

        return PostMetrics(
            reach=values.get("post_total_media_view_unique", 0),
            clicks=values.get("post_clicks", 0),
            likes=0,
            comments=comments,
            shares=shares,
            video_views=values.get("post_media_view", 0),
            extra={
                "reactions": reactions_total,
                "raw_fields": fields,
                "raw_insights": values,
                "insight_errors": errors,
                "insight_post_id": insight_post_id,
                "attempted_insight_post_ids": insight_candidates,
            },
        )

    def _resolve_post_fields(self, access_token: str, post_id: str) -> tuple[dict, list[str]]:
        fields = self._get_post_fields(access_token, post_id)
        candidate_ids = [fields.get("post_id")]
        page_id = self.credentials.get("page_id")
        if page_id and "_" not in str(post_id):
            candidate_ids.append(f"{page_id}_{post_id}")
        candidate_ids.append(post_id)

        deduped_candidate_ids = list(dict.fromkeys(str(candidate_id) for candidate_id in candidate_ids if candidate_id))
        best_fields = fields

        for candidate_id in deduped_candidate_ids:
            if not candidate_id or candidate_id == post_id:
                continue
            feed_fields = self._get_post_fields(access_token, candidate_id)
            if feed_fields:
                best_fields = {**fields, **feed_fields}
                break
        return best_fields, deduped_candidate_ids

    def _get_post_insights(self, access_token: str, post_ids: list[str]) -> tuple[dict, dict[str, str], str]:
        metric = ",".join(FACEBOOK_POST_INSIGHTS)
        errors_by_post_id: dict[str, str] = {}
        for post_id in post_ids:
            endpoint = f"{BASE_URL}/{post_id}/insights"
            try:
                resp = self._request(
                    "GET",
                    endpoint,
                    access_token=access_token,
                    params={"metric": metric},
                )
            except APIError as exc:
                errors_by_post_id[post_id] = str(exc)
                logger.warning("Skipping unsupported Facebook post insights at %s: %s", endpoint, exc)
                continue
            return parse_insights_response(resp.json()), {}, post_id

        error_text = "; ".join(f"{post_id}: {error}" for post_id, error in errors_by_post_id.items())
        return {}, {key: error_text for key in FACEBOOK_POST_INSIGHTS}, post_ids[0] if post_ids else ""

    def _get_post_fields(self, access_token: str, post_id: str) -> dict:
        # ``post_id`` is a Video-node field, not a field on a plain Post node, so
        # requesting it against a feed post can fail the whole call with an
        # invalid-field error. Retry without ``post_id`` so the engagement fields
        # (comments/shares/reactions summaries) still load for normal posts.
        field_sets = (FACEBOOK_POST_FIELDS, [f for f in FACEBOOK_POST_FIELDS if f != "post_id"])
        for fields in field_sets:
            try:
                fields_resp = self._request(
                    "GET",
                    f"{BASE_URL}/{post_id}",
                    access_token=access_token,
                    params={"fields": ",".join(fields)},
                )
                return fields_resp.json()
            except APIError as exc:
                logger.debug("Facebook post %s fields unavailable: %s", post_id, exc)
                if "post_id" not in str(exc):
                    # Only the invalid-`post_id`-field error is worth retrying
                    # without it; other errors (auth, 5xx, not-found) fail
                    # identically, so don't issue a second doomed request.
                    break
        return {}

    @staticmethod
    def _stored_post_id(graph_post_id: str) -> str:
        """Store only Facebook's post object id from PAGEID_POSTID values."""
        post_id = str(graph_post_id or "")
        if "_" in post_id:
            return post_id.rsplit("_", 1)[1]
        return post_id

    def _page_scoped_post_id(self, post_id: str) -> str:
        post_id = str(post_id or "")
        if "_" in post_id:
            return post_id
        page_id = self.credentials.get("page_id")
        if page_id and post_id:
            return f"{page_id}_{post_id}"
        return post_id

    @staticmethod
    def _summary_total(data: dict, key: str) -> int:
        value = data.get(key, {})
        if isinstance(value, int):
            return value
        if isinstance(value, dict):
            return value.get("summary", {}).get("total_count", 0) or 0
        return 0

    @staticmethod
    def _share_count(data: dict) -> int:
        value = data.get("shares", {})
        if isinstance(value, int):
            return value
        if isinstance(value, dict):
            return value.get("count", 0) or 0
        return 0

    def get_account_metrics(self, access_token: str, date_range: tuple[datetime, datetime]) -> AccountMetrics:
        page_id = self.credentials.get("page_id", "me")
        values, errors = fetch_insights_safe(
            self._request,
            platform=self.platform_name,
            endpoint=f"{BASE_URL}/{page_id}/insights",
            access_token=access_token,
            metrics=FACEBOOK_PAGE_INSIGHTS,
            base_params={
                "period": "day",
                "since": int(date_range[0].timestamp()),
                "until": int(date_range[1].timestamp()),
            },
            endpoint_type="page",
        )

        followers = 0
        try:
            page_resp = self._request(
                "GET",
                f"{BASE_URL}/{page_id}",
                access_token=access_token,
                params={"fields": "followers_count"},
            )
            followers = page_resp.json().get("followers_count", 0)
        except APIError as exc:
            logger.debug("Facebook page %s follower count unavailable: %s", page_id, exc)
        if not followers:
            followers = values.get("page_follows", 0)

        return AccountMetrics(
            followers=followers,
            followers_gained=values.get("page_daily_follows_unique", 0),
            reach=values.get("page_total_media_view_unique", 0),
            extra={
                "views": values.get("page_media_view", 0),
                "raw_insights": values,
                "insight_errors": errors,
            },
        )

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        """Poll Messenger DMs and Page-post comments.

        The two halves need different permissions (``pages_messaging`` vs.
        ``pages_read_user_content``) and fail independently, so one missing
        permission must not blank the other — a single raise here would abort
        the whole account's sync in ``InboxSyncEngine._sync_account``.
        """
        messages: list[InboxMessage] = []
        failures: list[Exception] = []

        for label, fetch in (("DM", self._fetch_direct_messages), ("comment", self._fetch_post_comments)):
            try:
                messages.extend(fetch(access_token, since))
            except Exception as exc:
                failures.append(exc)
                logger.warning("Facebook %s poll failed: %s", label, exc)

        # Nothing came back at all: surface the first error so the sync engine
        # logs a real cause instead of silently recording an empty poll.
        if failures and not messages:
            raise failures[0]
        return messages

    def _fetch_direct_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        page_id = self.credentials.get("page_id", "me")
        params: dict = {}
        if since:
            params["since"] = int(since.timestamp())

        resp = self._request(
            "GET",
            f"{BASE_URL}/{page_id}/conversations",
            access_token=access_token,
            params=params,
        )
        conversations = resp.json().get("data", [])

        messages: list[InboxMessage] = []
        for convo in conversations:
            convo_id = convo["id"]
            msg_resp = self._request(
                "GET",
                f"{BASE_URL}/{convo_id}/messages",
                access_token=access_token,
                params={"fields": "id,message,from,created_time"},
            )
            for msg in msg_resp.json().get("data", []):
                sender = msg.get("from", {})
                sender_id = str(sender.get("id", ""))
                # A conversation contains both sides. Without this the Page's
                # own replies come back on the next poll as fresh inbound DMs,
                # re-notifying the team and restarting their SLA clock.
                if sender_id and sender_id == str(page_id):
                    continue
                messages.append(
                    InboxMessage(
                        platform_message_id=msg["id"],
                        sender_id=sender_id,
                        sender_name=sender.get("name", ""),
                        text=msg.get("message", ""),
                        timestamp=datetime.fromisoformat(msg["created_time"].replace("+0000", "+00:00")),
                        message_type="dm",
                        # sender_id is the PSID the Send API needs to reply.
                        extra={"conversation_id": convo_id, "sender_id": sender_id},
                    )
                )
        return messages

    def _fetch_post_comments(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        """Poll comments on the Page's recent posts.

        The ``feed`` webhook delivers these in near real time, but only when the
        Page subscription *and* the app's Webhooks config are both in place. A
        Page missing either is otherwise deaf to comments forever, with no way
        to backfill — this poll is what makes that recoverable.
        """
        # No page_id means the own-comment filter below cannot recognise our own
        # activity, which would ingest the Page's own first comments as inbound
        # customer messages. Refuse to poll rather than do that.
        page_id = str(self.credentials.get("page_id") or "")
        if not page_id:
            logger.warning("Skipping Facebook comment poll: no page_id in credentials")
            return []

        # ``since`` on the /feed edge filters by POST creation time, not comment
        # time, so it can only bound how far back we look for *posts*. Passing
        # the caller's ``since`` here would hide every new comment on an older
        # post. Comments are filtered on their own timestamp below.
        feed_floor = datetime.now(UTC) - timedelta(days=FACEBOOK_FEED_WINDOW_DAYS)
        resp = self._request(
            "GET",
            f"{BASE_URL}/{page_id}/feed",
            access_token=access_token,
            params={
                "fields": (
                    "id,created_time,permalink_url,"
                    f"comments.limit({FACEBOOK_COMMENTS_PER_POST})"
                    f"{{{FACEBOOK_COMMENT_FIELDS}}}"
                ),
                "limit": FACEBOOK_FEED_SCAN_LIMIT,
                "since": int(feed_floor.timestamp()),
            },
        )

        # Normalize once here so the per-comment compare can never mix an aware
        # Graph timestamp with a naive caller-supplied ``since``.
        cutoff = None
        if since:
            cutoff = (since if since.tzinfo else since.replace(tzinfo=UTC)) - timedelta(
                hours=FACEBOOK_COMMENT_LOOKBACK_HOURS
            )
        messages: list[InboxMessage] = []
        seen: set[str] = set()

        for post in resp.json().get("data", []):
            # One unreadable or over-paginated post must not discard the
            # comments already collected from every earlier post in this poll.
            try:
                comments = post.get("comments") or {}
                for comment in self._iter_comments(access_token, comments):
                    message = self._comment_to_message(comment, post, page_id, cutoff, seen)
                    if message is not None:
                        messages.append(message)
            except Exception as exc:
                logger.warning("Skipping Facebook comments for post %s: %s", post.get("id"), exc)

        logger.debug("Facebook comment poll for page %s produced %d message(s)", page_id, len(messages))
        return messages

    def _iter_comments(self, access_token: str, comments: dict):
        """Yield a post's comments, following at most a bounded number of pages."""
        pages = 0
        while comments:
            yield from comments.get("data", [])

            next_url = (comments.get("paging") or {}).get("next")
            pages += 1
            if not next_url or pages >= FACEBOOK_COMMENT_PAGE_LIMIT:
                if next_url:
                    logger.debug("Facebook comment pagination capped at %d pages", FACEBOOK_COMMENT_PAGE_LIMIT)
                return
            # Pin the cursor to Graph's host — this is a URL from a response
            # body. And re-send the token: ``_request`` authenticates with an
            # Authorization header, so Graph builds ``paging.next`` from a query
            # string that never contained one.
            if urlparse(next_url).netloc != urlparse(BASE_URL).netloc:
                logger.warning("Ignoring off-host Facebook comment paging URL")
                return
            comments = self._request("GET", next_url, access_token=access_token).json()

    def _comment_to_message(
        self,
        comment: dict,
        post: dict,
        page_id: str,
        cutoff: datetime | None,
        seen: set[str],
    ) -> InboxMessage | None:
        """Convert one Graph comment to an InboxMessage, or None to skip it."""
        comment_id = str(comment.get("id") or "")
        if not comment_id or comment_id in seen:
            return None

        author = comment.get("from") or {}
        author_id = str(author.get("id") or "")
        # The Page's own comments — including the first comment we post
        # ourselves — must not come back as inbound messages. An absent author
        # means a privacy-restricted third party: the Page's own comments always
        # carry ``from``, so keep those rather than dropping them.
        if author_id and author_id == str(page_id):
            return None

        timestamp = self._parse_graph_time(comment.get("created_time"))
        if timestamp is None:
            logger.debug("Skipping Facebook comment %s with unparseable created_time", comment_id)
            return None
        if cutoff and timestamp < cutoff:
            return None

        seen.add(comment_id)
        graph_post_id = str(post.get("id") or "")
        return InboxMessage(
            platform_message_id=comment_id,
            sender_id=author_id,
            sender_name=author.get("name", ""),
            text=comment.get("message", ""),
            timestamp=timestamp,
            message_type="comment",
            extra={
                "comment_id": comment_id,
                "post_id": graph_post_id,
                # Matches PlatformPost.platform_post_id, which stores the id
                # without the page prefix — used to link related_post.
                "stored_post_id": self._stored_post_id(graph_post_id),
                "parent_id": str((comment.get("parent") or {}).get("id") or ""),
                "permalink_url": comment.get("permalink_url", ""),
                "post_permalink_url": post.get("permalink_url", ""),
                "sender_handle": author_id,
                "reply_edge": "comment",
                "source": "poll",
            },
        )

    @staticmethod
    def _parse_graph_time(value: str | None) -> datetime | None:
        """Parse Graph's ``2026-08-07T12:34:56+0000`` timestamps.

        Always returns an aware datetime. A value without an offset would
        otherwise be compared against an aware cutoff (TypeError) and stored as
        a naive ``received_at``; Graph serves UTC, so assume it.
        """
        return parse_graph_time(value)

    def reply_to_message(
        self,
        access_token: str,
        message_id: str,
        text: str,
        extra: dict | None = None,
        *,
        human_agent: bool = False,
    ) -> ReplyResult:
        """Send a Messenger reply from the Page via the Send API.

        Messages go to ``/{page-id}/messages`` addressed to the person's PSID —
        not to the message or conversation ID, which is not a Send API target.
        """
        psid = resolve_recipient_id(extra)
        if not psid:
            raise APIError(
                "Cannot send the reply: no page-scoped ID for the recipient. "
                "The original message is missing its sender details.",
                platform=self.platform_name,
            )

        page_id = self.credentials.get("page_id", "me")
        payload = build_send_payload(psid, text, human_agent=human_agent)

        resp = self._request(
            "POST",
            f"{BASE_URL}/{page_id}/messages",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        return ReplyResult(platform_message_id=data.get("message_id", ""), extra=data)

    def reply_to_comment(self, access_token: str, comment_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        """Reply to a comment or mention by commenting on it.

        Facebook threads comments only two levels deep, so replying *to a reply*
        must target its parent — posting to a second-level comment's own
        ``comments`` edge is rejected.

        ``parent_id`` is only usable when it names a *comment*. The ``feed``
        webhook sets it to the POST id for a top-level comment, and targeting
        that would publish a new top-level comment on the post instead of
        answering the person — so a parent that matches the post is ignored.
        """
        target = self._comment_reply_target(comment_id, extra)
        resp = self._request(
            "POST",
            f"{BASE_URL}/{target}/comments",
            access_token=access_token,
            json={"message": text},
        )
        data = resp.json()
        return ReplyResult(platform_message_id=data.get("id", ""), extra=data)

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def subscribe_webhooks(self, access_token: str, account_id: str) -> bool:
        """Subscribe this app to the Page's feed, mention and message webhooks."""
        resp = self._request(
            "POST",
            f"{BASE_URL}/{account_id}/subscribed_apps",
            access_token=access_token,
            params={"subscribed_fields": ",".join(FACEBOOK_WEBHOOK_FIELDS)},
        )
        return bool(resp.json().get("success"))

    @staticmethod
    def _comment_reply_target(comment_id: str, extra: dict | None) -> str:
        """The node a reply to ``comment_id`` should be posted on.

        Returns the parent comment for a nested reply, and the comment itself
        otherwise. A ``parent_id`` equal to the post (what the ``feed`` webhook
        reports for every top-level comment) is not a comment parent and must
        not be used, or the reply becomes a new top-level post comment.
        """
        extra = extra or {}
        parent_id = str(extra.get("parent_id") or "")
        if not parent_id:
            return comment_id

        post_ids = {
            str(extra.get("post_id") or ""),
            str(extra.get("stored_post_id") or ""),
        }
        post_ids.discard("")
        if parent_id in post_ids or FacebookProvider._stored_post_id(parent_id) in post_ids:
            return comment_id
        return parent_id

    def get_webhook_subscriptions(self, access_token: str, account_id: str) -> list[dict]:
        """List the apps subscribed to this Page and the fields each receives."""
        resp = self._request(
            "GET",
            f"{BASE_URL}/{account_id}/subscribed_apps",
            access_token=access_token,
            params={"fields": "id,name,subscribed_fields"},
        )
        return resp.json().get("data", [])

    def unsubscribe_webhooks(self, access_token: str, account_id: str) -> bool:
        resp = self._request(
            "DELETE",
            f"{BASE_URL}/{account_id}/subscribed_apps",
            access_token=access_token,
        )
        return bool(resp.json().get("success"))

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def debug_token(self, access_token: str) -> dict:
        """Inspect a token: validity, type, expiry and the scopes it carries.

        ``/me/permissions`` answers for a *user* token; a Page token has to go
        through ``/debug_token`` with an app token, which is why this exists
        separately from the OAuth flow.
        """
        app_id = self.credentials.get("client_id", "")
        app_secret = self.credentials.get("client_secret", "")
        if not app_id or not app_secret:
            raise APIError(
                "App credentials are required to inspect a Facebook token",
                platform=self.platform_name,
            )
        resp = self._request(
            "GET",
            f"{BASE_URL}/debug_token",
            params={"input_token": access_token, "access_token": f"{app_id}|{app_secret}"},
        )
        return resp.json().get("data", {})

    def revoke_token(self, access_token: str) -> bool:
        try:
            self._request(
                "DELETE",
                f"{BASE_URL}/me/permissions",
                access_token=access_token,
            )
            return True
        except APIError:
            logger.warning("Failed to revoke Facebook token")
            return False
