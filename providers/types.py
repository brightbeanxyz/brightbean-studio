"""Shared data types for social platform providers."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime


class PostType(enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"
    LINK = "link"
    ARTICLE = "article"
    POLL = "poll"
    PIN = "pin"
    SHORT = "short"


class MediaType(enum.Enum):
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    MP4 = "mp4"
    MOV = "mov"
    WEBP = "webp"
    PDF = "pdf"


class AuthType(enum.Enum):
    OAUTH2 = "oauth2"
    SESSION = "session"
    INSTANCE_OAUTH = "instance_oauth"


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str = "Bearer"
    scope: str | None = None
    raw_response: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AccountProfile:
    platform_id: str
    name: str
    handle: str | None = None
    avatar_url: str | None = None
    follower_count: int = 0
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PublishResult:
    platform_post_id: str
    url: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CommentResult:
    platform_comment_id: str
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PostMetrics:
    impressions: int = 0
    reach: int = 0
    engagements: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    video_views: int = 0
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AccountMetrics:
    followers: int | None = 0
    followers_gained: int = 0
    impressions: int = 0
    reach: int = 0
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Demographics:
    age_ranges: dict = field(default_factory=dict)
    genders: dict = field(default_factory=dict)
    top_countries: dict = field(default_factory=dict)
    top_cities: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class InboxMessage:
    platform_message_id: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: datetime
    message_type: str = "comment"
    is_read: bool = False
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ReplyResult:
    platform_message_id: str
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_hour: int = 200
    requests_per_day: int = 5000
    publish_per_day: int = 25
    extra: dict = field(default_factory=dict)


@dataclass
class PublishContent:
    """Content payload passed to publish_post()."""

    text: str = ""
    media_urls: list[str] = field(default_factory=list)
    media_files: list[str] = field(default_factory=list)
    post_type: PostType = PostType.TEXT
    link_url: str | None = None
    title: str | None = None
    description: str | None = None
    first_comment: str | None = None
    extra: dict = field(default_factory=dict)
    # Duration of the primary video in seconds, when known. Lets providers
    # enforce platform limits (e.g. TikTok's max_video_post_duration_sec).
    video_duration_sec: float | None = None
