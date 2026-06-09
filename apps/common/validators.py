"""Shared validation utilities."""

import ipaddress
import re
import socket
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

MAX_TAGS = 25
MAX_TAG_LENGTH = 100

MAX_YT_TAGS_TOTAL_CHARS = 500
MAX_YT_TAG_LENGTH = 50

# Cap external XML payloads (RSS/Atom feeds, webhook bodies) before parsing.
# 5 MB is large enough for any reasonable feed while bounding memory pressure
# from runaway documents.
MAX_XML_BYTES = 5 * 1024 * 1024

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def is_safe_url(url: str) -> bool:
    """Validate that a URL is http(s) and does not resolve to a private/reserved IP.

    Returns False for non-http(s) schemes (file://, gopher://, etc.) and for URLs
    whose hostname resolves to any private, reserved, loopback, or link-local
    address. Checks every resolved address to defend against DNS responses that
    include multiple A/AAAA records.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        addr_infos = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
        for _family, _, _, _, sockaddr in addr_infos:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                return False

        return True
    except (socket.gaierror, ValueError, OSError):
        return False


def resolve_public_ip(url: str) -> str | None:
    """Resolve url's hostname to a public IPv4/IPv6 string, or return None.

    Unlike is_safe_url (which only returns True/False), this returns the actual
    resolved IP so callers can connect to that fixed address — closing the
    DNS-rebinding TOCTOU between validation and connect.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        hostname = parsed.hostname
        if not hostname:
            return None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addr_infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        for _family, _, _, _, sockaddr in addr_infos:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                return None
        # Return the first family's IP. Caller will Host-pin against it.
        return str(addr_infos[0][4][0])
    except (socket.gaierror, ValueError, OSError):
        return None


def normalize_tags(raw) -> list[str]:
    """Strict tag normalization for JSON API endpoints.

    Raises ValueError on malformed input or overflow — caller returns HTTP 400.
    """
    if not isinstance(raw, list):
        raise ValueError("tags must be a list")
    if len(raw) > MAX_TAGS:
        raise ValueError(f"too many tags (max {MAX_TAGS})")
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        if not isinstance(t, str):
            raise ValueError("each tag must be a string")
        t = t.strip()
        if not t:
            continue
        if len(t) > MAX_TAG_LENGTH:
            raise ValueError(f"tag too long (max {MAX_TAG_LENGTH} chars)")
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def parse_and_truncate_tag_string(raw: str) -> list[str]:
    """Lenient tag normalization for HTML form POSTs.

    Splits a comma-separated string, strips whitespace, truncates each tag to
    MAX_TAG_LENGTH, deduplicates, and caps total count at MAX_TAGS. Excess input
    is silently dropped — render-time HTML escape is the security boundary.
    """
    if not raw:
        return []
    parts = [t.strip() for t in raw.split(",") if t.strip()]
    out: list[str] = []
    seen: set[str] = set()
    for t in parts:
        if len(out) >= MAX_TAGS:
            break
        t = t[:MAX_TAG_LENGTH]
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def validate_hex_color(value: str) -> None:
    """Reject any string that isn't a 6-digit hex color (#RRGGBB) or empty.

    Used as a model-field validator on every user-editable color column.
    Empty strings pass so that "no override" still works.
    """
    if value in ("", None):
        return
    if not isinstance(value, str) or not _HEX_COLOR_RE.match(value):
        raise ValidationError("Color must be a 6-digit hex value like #3B82F6.")


def is_valid_hex_color(value: str) -> bool:
    """Boolean form of validate_hex_color for view-layer rejection paths."""
    if value in ("", None):
        return True
    return isinstance(value, str) and bool(_HEX_COLOR_RE.match(value))


def safe_xml_fromstring(body: bytes, *, max_bytes: int = MAX_XML_BYTES) -> ET.Element | None:
    """Parse RSS/Atom/Webhook XML safely.

    Hardens against billion-laughs / quadratic-blowup attacks WITHOUT pulling in
    the `defusedxml` dependency: we cap body size and reject any document that
    declares a DTD or internal entities. Legitimate RSS/Atom/PubSubHubbub
    payloads never need either.

    Returns the parsed root element, or None for any reject path (oversized,
    DTD/entity-bearing, or malformed XML). Callers should treat None as
    "discard this payload" rather than retry.
    """
    if not isinstance(body, bytes | bytearray):
        return None
    if len(body) > max_bytes:
        return None
    # DOCTYPE / ENTITY declarations must appear in the prolog (before the root
    # element). Scanning the first 4 KB case-insensitively reliably catches
    # them without parsing the whole document.
    head = bytes(body[:4096]).lower()
    if b"<!doctype" in head or b"<!entity" in head:
        return None
    try:
        return ET.fromstring(body)
    except ET.ParseError:
        return None


def parse_and_truncate_youtube_tag_string(raw: str) -> list[str]:
    """YouTube-specific tag normalization for HTML form POSTs.

    YouTube's Data API caps total tag-list characters at 500 (delimiters counted);
    we cap individual tag length at MAX_YT_TAG_LENGTH as a defensive bound. Excess
    input is silently dropped.
    """
    if not raw:
        return []
    parts = [t.strip() for t in raw.split(",") if t.strip()]
    out: list[str] = []
    seen: set[str] = set()
    total = 0
    for t in parts:
        t = t[:MAX_YT_TAG_LENGTH]
        if t in seen:
            continue
        cost = len(t) + (1 if out else 0)
        if total + cost > MAX_YT_TAGS_TOTAL_CHARS:
            break
        seen.add(t)
        out.append(t)
        total += cost
    return out
