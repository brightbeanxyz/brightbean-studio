"""File validation for media library uploads."""

import contextlib
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.utils.text import get_valid_filename

ALLOWED_MIME_TYPES = {
    "image": [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    ],
    "video": [
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/webm",
    ],
    "document": [
        "application/pdf",
    ],
}

MIME_TO_FILE_TYPE = {}
for file_type, mimes in ALLOWED_MIME_TYPES.items():
    for mime in mimes:
        MIME_TO_FILE_TYPE[mime] = "gif" if mime == "image/gif" else file_type

ALL_ALLOWED_MIMES = set()
for mimes in ALLOWED_MIME_TYPES.values():
    ALL_ALLOWED_MIMES.update(mimes)

ALLOWED_EXTENSIONS = {
    "image": ["jpg", "jpeg", "png", "webp", "gif"],
    "video": ["mp4", "mov", "avi", "webm"],
    "document": ["pdf"],
}

ALL_ALLOWED_EXTENSIONS = set()
for exts in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(exts)

# The one extension each allowed MIME is stored under. Sniffing the magic bytes
# settles what a file *is*; this settles what it is *named*, which is a separate
# problem. Both django.views.static.serve and Caddy's file_server derive
# Content-Type from the suffix, so a PNG/HTML polyglot uploaded as "poc.html"
# passes the magic-byte check and is then served as text/html from the app's own
# origin — same-origin script, and on the Caddy path without even a CSP header
# to stop it. Keep a value here for every member of ALL_ALLOWED_MIMES;
# tests/../test_upload_filenames.py pins that.
CANONICAL_EXTENSION = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/x-msvideo": "avi",
    "video/webm": "webm",
    "application/pdf": "pdf",
}

MAX_FILE_SIZES = {
    "image": getattr(settings, "MEDIA_LIBRARY_MAX_IMAGE_SIZE", 20 * 1024 * 1024),
    "gif": getattr(settings, "MEDIA_LIBRARY_MAX_IMAGE_SIZE", 20 * 1024 * 1024),
    "video": getattr(settings, "MEDIA_LIBRARY_MAX_VIDEO_SIZE", 1024 * 1024 * 1024),
    "document": getattr(settings, "MEDIA_LIBRARY_MAX_IMAGE_SIZE", 20 * 1024 * 1024),
}


def determine_file_type(mime_type):
    """Map a MIME type to our FileType enum value."""
    return MIME_TO_FILE_TYPE.get(mime_type)


def storage_filename(original_name, sniffed_mime):
    """The name to store an upload under: the caller's stem, our extension.

    ``MediaAsset.filename`` keeps whatever the uploader called it for display;
    this is only the key on disk or in the bucket. Swapping the suffix for the
    one the sniffed bytes justify is what stops an upload from choosing the
    Content-Type it will later be served with — see CANONICAL_EXTENSION.
    """
    extension = CANONICAL_EXTENSION.get(sniffed_mime)
    if not extension:
        # Unreachable via validate_file(), which rejects anything outside
        # ALL_ALLOWED_MIMES first. Fall back to a suffix no server will hand
        # back as script rather than trusting the client's.
        extension = "bin"

    # Leading dots go too: ".htaccess" is all stem to pathlib, and a dotfile is
    # not a name we want to create inside MEDIA_ROOT.
    stem = Path(original_name or "").stem.strip().lstrip(".")
    try:
        stem = get_valid_filename(stem)
    except SuspiciousFileOperation:
        # Raised for a name that is empty, or that sanitises down to nothing.
        stem = ""

    return f"{stem or 'upload'}.{extension}"


# Magic-byte signatures for sniffing the *real* MIME of an uploaded file.
# Trusting `uploaded_file.content_type` is unsafe because that value is set by
# the client. Sniffing the first bytes prevents masquerade attacks (e.g. an
# HTML payload labelled as image/jpeg that, when served from same-origin
# storage, executes script in the user's browser).
def sniff_mime(file_obj):
    """Return the sniffed MIME type for an uploaded-file-like object, or None.

    Reads the first 32 bytes and matches them against a small allowlist of
    well-known signatures. Always restores the read position. Returns None for
    any unknown / mismatched signature — callers should treat that as a hard
    reject rather than a soft "unknown".
    """
    if not hasattr(file_obj, "read") or not hasattr(file_obj, "seek"):
        return None
    import contextlib

    try:
        file_obj.seek(0)
        head = file_obj.read(32)
    except (OSError, ValueError):
        return None
    finally:
        with contextlib.suppress(OSError, ValueError):
            file_obj.seek(0)

    if not isinstance(head, (bytes, bytearray)):
        return None
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp":
        # ISO Base Media: covers MP4, MOV/QuickTime, M4V. Brand-sniffing would
        # let us split mov from mp4, but our allow-list treats both as video.
        brand = head[8:12]
        if brand in (b"qt  ",):
            return "video/quicktime"
        return "video/mp4"
    if head.startswith(b"\x1aE\xdf\xa3"):
        return "video/webm"
    if head.startswith(b"RIFF") and head[8:12] == b"AVI ":
        return "video/x-msvideo"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def validate_file(uploaded_file):
    """Validate an uploaded file. Returns (file_type, errors).

    Trusts the sniffed magic bytes, not the client-supplied Content-Type. The
    client header is only used to size-check before we read the body; the
    file's declared media_type is set from the sniffed value by the caller.
    """
    errors = []

    sniffed = sniff_mime(uploaded_file)
    if not sniffed or sniffed not in ALL_ALLOWED_MIMES:
        # Reject. We do not echo back the client-supplied content_type because
        # that's misleading when the magic doesn't match.
        errors.append("Unsupported or unrecognised file type.")
        return None, errors

    file_type = determine_file_type(sniffed)
    if not file_type:
        errors.append("Unsupported file type.")
        return None, errors

    max_size = MAX_FILE_SIZES.get(file_type, 20 * 1024 * 1024)
    if uploaded_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        errors.append(f"File too large. Maximum size for {file_type} files is {max_mb:.0f}MB.")

    if file_type in ("image", "gif"):
        errors.extend(_image_pixel_errors(uploaded_file))

    return file_type, errors


def _image_pixel_errors(uploaded_file) -> list[str]:
    """Reject images whose decoded size would blow the worker's memory budget.

    File size does not bound this: a highly compressible image can be tiny on
    disk and enormous decoded, and decoded cost is what the worker pays. The
    worker has to enforce the ceiling itself because presigned
    direct-to-storage uploads never pass through here, but checking it on the
    synchronous path means the common case is told at upload time instead of
    silently landing in FAILED minutes later.

    Goes through ``open_image`` with the same ``draft_size`` the thumbnail path
    uses, rather than measuring the header here, so the two agree by
    construction. Measuring raw header dimensions would reject a 40MP JPEG that
    the worker thumbnails without trouble — the JPEG decoder downscales during
    the read — and would make a REST upload behave differently from a presigned
    one for the same file.

    Imported lazily because ``services`` imports this module; at module level it
    would be circular.

    Anything unreadable is left alone: ``sniff_mime`` has already vouched for
    the magic bytes, and a Pillow failure here is not this function's to report.
    """
    from django.conf import settings

    from .services import ImageTooLargeError, open_image

    thumb_size = getattr(settings, "MEDIA_LIBRARY_THUMBNAIL_SIZE", (400, 400))

    try:
        with open_image(uploaded_file, draft_size=thumb_size):
            return []
    except ImageTooLargeError as exc:
        return [str(exc)]
    except Exception:
        return []
    finally:
        # The caller stores this file next; a consumed handle writes nothing.
        with contextlib.suppress(OSError, ValueError):
            uploaded_file.seek(0)


def get_accepted_file_types():
    """Return a comma-separated string of accepted MIME types for HTML file input."""
    return ",".join(sorted(ALL_ALLOWED_MIMES))
