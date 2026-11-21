"""Optional Instagram container fields kept in ``PlatformPost.platform_extra``.

Shared by both Instagram connections (Facebook Login and Instagram Login),
which build the same media containers against different hosts.
"""

from __future__ import annotations

import re

# Meta: "A list of up to 3 instagram usernames as collaborators".
MAX_COLLABORATORS = 3


def clean_collaborators(value: object) -> list[str]:
    """Usernames from free text or a list: no "@", no blanks, no repeats.

    Does not trim to ``MAX_COLLABORATORS``; dropping a name silently would
    publish a post the author did not ask for, so callers reject instead.
    """
    if isinstance(value, str):
        parts = re.split(r"[\s,]+", value)
    elif isinstance(value, list | tuple):
        parts = [str(v) for v in value]
    else:
        return []
    names: list[str] = []
    seen: set[str] = set()
    for part in parts:
        name = part.strip().lstrip("@")
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def container_options(extra: dict, *, reel: bool) -> dict:
    """Collaborators, plus the cover frame as ``thumb_offset`` for a Reel.

    Callers leave stories out: Meta supports neither field there.
    """
    options: dict = {}
    collaborators = clean_collaborators(extra.get("collaborators"))
    if collaborators:
        options["collaborators"] = collaborators
    if reel:
        try:
            # int(), not str.isdigit(): isdigit() accepts "²", which int() rejects.
            cover_ms = int(extra.get("video_cover_timestamp_ms"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            cover_ms = -1
        if cover_ms >= 0:
            options["thumb_offset"] = cover_ms
    return options
