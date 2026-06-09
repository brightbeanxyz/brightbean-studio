"""Security regression tests for media_library uploads (V3 + V8)."""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.media_library.services import create_asset
from apps.media_library.validators import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    sniff_mime,
    validate_file,
)
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 14
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 28


class SvgDisallowedTest(SimpleTestCase):
    """V3: SVG must be stripped from the upload allow-list entirely."""

    def test_svg_not_in_allowed_mimes(self):
        self.assertNotIn("image/svg+xml", ALLOWED_MIME_TYPES["image"])

    def test_svg_not_in_allowed_extensions(self):
        self.assertNotIn("svg", ALLOWED_EXTENSIONS["image"])


class SniffMimeTest(SimpleTestCase):
    """V8: magic-byte sniffer must catch spoofed content-types."""

    def test_recognises_jpeg(self):
        f = SimpleUploadedFile("a.jpg", JPEG, content_type="application/octet-stream")
        self.assertEqual(sniff_mime(f), "image/jpeg")

    def test_recognises_png(self):
        f = SimpleUploadedFile("a.png", PNG, content_type="text/html")
        self.assertEqual(sniff_mime(f), "image/png")

    def test_rejects_unknown_signature(self):
        f = SimpleUploadedFile("evil.jpg", b"<svg><script>alert(1)</script></svg>", content_type="image/jpeg")
        self.assertIsNone(sniff_mime(f))

    def test_validate_file_rejects_html_labelled_as_jpeg(self):
        f = SimpleUploadedFile(
            "fake.jpg",
            b"<html><body>not a jpeg</body></html>",
            content_type="image/jpeg",
        )
        file_type, errors = validate_file(f)
        self.assertIsNone(file_type)
        self.assertTrue(errors)

    def test_validate_file_accepts_real_jpeg(self):
        f = SimpleUploadedFile("real.jpg", JPEG, content_type="image/jpeg")
        f.size = len(JPEG)
        file_type, errors = validate_file(f)
        self.assertEqual(file_type, "image")
        self.assertEqual(errors, [])


class CreateAssetMimeSourceTest(TestCase):
    """V8: stored mime_type comes from the sniffer, NOT the client header."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.user = User.objects.create_user(
            email="up@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )

    def test_uploaded_content_type_is_overridden_by_sniff(self):
        # Client lies about content_type, sending JPEG bytes labelled as PNG.
        uploaded = SimpleUploadedFile("a.jpg", JPEG, content_type="image/png")
        asset = create_asset(self.org, self.workspace, uploaded, self.user)
        self.assertEqual(asset.mime_type, "image/jpeg")
        self.assertEqual(asset.media_type, "image")

    def test_rejects_html_payload_labelled_as_image(self):
        uploaded = SimpleUploadedFile(
            "fake.jpg",
            b"<html><body>hi</body></html>",
            content_type="image/jpeg",
        )
        with self.assertRaises(ValidationError):
            create_asset(self.org, self.workspace, uploaded, self.user)
