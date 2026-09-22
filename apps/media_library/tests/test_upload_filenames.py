"""Uploads must not choose the Content-Type they are later served with.

``validate_file`` sniffs magic bytes, which settles what a file *is*. It says
nothing about what the file is *named*, and both ``django.views.static.serve``
and Caddy's ``file_server`` derive ``Content-Type`` from the stored suffix. A
PNG/HTML polyglot — real PNG header, ``<script>`` further in — uploaded as
``poc.html`` therefore passed validation and came back as ``text/html`` from the
app's own origin, which on the Caddy path carries no CSP header either.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.media_library.services import create_asset
from apps.media_library.validators import (
    ALL_ALLOWED_MIMES,
    CANONICAL_EXTENSION,
    storage_filename,
)
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="bb-test-upload-names-")

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
# Valid PNG magic, then markup. sniff_mime() only reads the header.
POLYGLOT = PNG_HEADER + b"\x00" * 8 + b"<script>alert(document.domain)</script>"


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


def test_every_allowed_mime_has_a_canonical_extension():
    """A gap here would silently fall back to .bin and break the upload."""
    assert set(CANONICAL_EXTENSION) == ALL_ALLOWED_MIMES


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("poc.html", "poc.png"),
        ("poc.svg", "poc.png"),
        ("holiday snap.PNG", "holiday_snap.png"),
        ("archive.tar.gz", "archive.tar.png"),
        (".htaccess", "htaccess.png"),
        ("", "upload.png"),
    ],
)
def test_storage_filename_replaces_the_clients_extension(original, expected):
    assert storage_filename(original, "image/png") == expected


def test_storage_filename_cannot_escape_the_upload_directory():
    assert "/" not in storage_filename("../../etc/passwd", "image/png")


@pytest.mark.django_db
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
def test_polyglot_upload_is_stored_under_a_png_suffix():
    user = User.objects.create_user(
        email="uploader@example.com",
        password="testpass123",
        tos_accepted_at=timezone.now(),
    )
    org = Organization.objects.create(name="Test Org")
    workspace = Workspace.objects.create(organization=org, name="Test Workspace")

    asset = create_asset(
        org,
        workspace,
        SimpleUploadedFile("poc.html", POLYGLOT, content_type="image/png"),
        user,
    )

    assert Path(asset.file.name).suffix == ".png"
    assert not asset.file.name.endswith(".html")
    # The uploader's own name survives for display; only the key changed.
    assert asset.filename == "poc.html"
    assert asset.mime_type == "image/png"
