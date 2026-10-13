"""Optional container fields shared by the two Instagram providers.

Instagram via Facebook Login and Instagram Login both create media containers
on the same IG User Media edge, so the optional fields the composer can set
are mapped onto the container payload here, once, for both.

https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
"""

from __future__ import annotations

import contextlib


def ai_disclosure_fields(extra: dict) -> dict:
    """``is_ai_generated``: the creator's self-disclosure of AI use.

    Meta requires the disclosure before sharing realistic video or
    realistic-sounding audio that was made or altered with AI (its own example
    is a Reel narrated by a realistic AI voiceover), and the app only offers it
    at share time, so a scheduler that cannot send it cannot publish that kind
    of post compliantly.

    The reference rules the field out on carousel children only, so carousels
    carry it on the parent container. Stories are left alone: the field is not
    documented for them, and a rejected field would fail the whole publish.
    """
    return {"is_ai_generated": True} if extra.get("is_ai_generated") else {}


def reel_cover_fields(extra: dict) -> dict:
    """``thumb_offset``: the frame, in milliseconds, used as the Reel's cover.

    Without it Instagram takes the first frame, which in edited videos is often
    a blank intro. The composer stores the offset under the same
    ``video_cover_timestamp_ms`` key as the TikTok cover, from the same frame
    picker. A missing, negative or unparseable value sends nothing, so
    Instagram keeps its default rather than rejecting the container.
    """
    cover_ms = extra.get("video_cover_timestamp_ms")
    if cover_ms is None or isinstance(cover_ms, bool):
        return {}
    with contextlib.suppress(TypeError, ValueError):
        cover_ms = int(cover_ms)
        if cover_ms >= 0:
            return {"thumb_offset": cover_ms}
    return {}
