"""File validation for media library uploads."""

from django.conf import settings

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

MAX_FILE_SIZES = {
    "image": getattr(settings, "MEDIA_LIBRARY_MAX_IMAGE_SIZE", 20 * 1024 * 1024),
    "gif": getattr(settings, "MEDIA_LIBRARY_MAX_IMAGE_SIZE", 20 * 1024 * 1024),
    "video": getattr(settings, "MEDIA_LIBRARY_MAX_VIDEO_SIZE", 1024 * 1024 * 1024),
    "document": getattr(settings, "MEDIA_LIBRARY_MAX_IMAGE_SIZE", 20 * 1024 * 1024),
}


def determine_file_type(mime_type):
    """Map a MIME type to our FileType enum value."""
    return MIME_TO_FILE_TYPE.get(mime_type)


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

    return file_type, errors


def get_accepted_file_types():
    """Return a comma-separated string of accepted MIME types for HTML file input."""
    return ",".join(sorted(ALL_ALLOWED_MIMES))
