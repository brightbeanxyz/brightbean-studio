"""Tests for the Pillow seam in ``apps.media_library.services``.

These paths had no coverage at all, which is uncomfortable given what they do:
they are the only place the worker decodes attacker-supplied pixel data, and an
unbounded decode is what put the Heroku worker over its 512 MB quota. The cases
below pin the two properties that matter — the decode is bounded, and the
thumbnail still looks right for every format we accept.
"""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.media_library.services import (
    ImageTooLargeError,
    apply_image_edits,
    extract_image_metadata,
    generate_image_thumbnail,
    open_image,
)
from apps.media_library.validators import validate_file


def _encode(img, fmt):
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


def _jpeg(width=1200, height=800, mode="RGB"):
    return _encode(Image.new(mode, (width, height), (120, 30, 200)), "JPEG")


def _alpha_png(width=600, height=400):
    return _encode(Image.new("RGBA", (width, height), (10, 200, 90, 128)), "PNG")


def _palette_png(width=600, height=400):
    return _encode(Image.new("RGB", (width, height), (200, 40, 40)).convert("P"), "PNG")


class OpenImageGuardTest(SimpleTestCase):
    def test_rejects_an_image_over_the_pixel_limit(self):
        # 600x400 = 240_000 px, so a limit just under it must reject.
        with (
            override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000),
            self.assertRaises(ImageTooLargeError),
            open_image(_alpha_png()),
        ):
            pass

    def test_error_names_the_dimensions_and_the_limit(self):
        with (
            override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000),
            self.assertRaises(ImageTooLargeError) as ctx,
            open_image(_alpha_png()),
        ):
            pass
        message = str(ctx.exception)
        assert "600x400" in message
        assert "megapixels" in message

    def test_allows_an_image_under_the_limit(self):
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=1_000_000), open_image(_alpha_png()) as img:
            assert img.size == (600, 400)

    def test_draft_lets_a_large_jpeg_through_on_its_reduced_size(self):
        """A JPEG's header dimensions are not what it costs us to decode.

        The decoder downscales during the read, so judging a JPEG on its full
        size would refuse a file that never allocates that much. 2400x1600 is
        3.84M px, but drafted for a 400x400 thumbnail it decodes far smaller.
        """
        with (
            override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=1_000_000),
            open_image(_jpeg(2400, 1600), draft_size=(400, 400)) as img,
        ):
            assert img.width * img.height <= 1_000_000

    def test_a_png_of_the_same_size_is_rejected(self):
        """PNG has no draft support, so it really does decode full-size."""
        with (
            override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=1_000_000),
            self.assertRaises(ImageTooLargeError),
            open_image(_alpha_png(2400, 1600), draft_size=(400, 400)),
        ):
            pass

    def test_does_not_close_a_caller_supplied_file_object(self):
        """``_process_image`` opens the same FieldFile twice, in sequence."""
        handle = _alpha_png()
        with open_image(handle):
            pass
        assert not handle.closed
        with open_image(handle) as img:
            assert img.size == (600, 400)


class GenerateImageThumbnailTest(SimpleTestCase):
    def test_rgb_jpeg(self):
        thumb = generate_image_thumbnail(_jpeg())
        assert thumb is not None
        with Image.open(io.BytesIO(thumb.read())) as out:
            assert out.format == "JPEG"
            assert out.mode == "RGB"
            assert max(out.size) <= 400

    def test_alpha_png_is_flattened_onto_white(self):
        thumb = generate_image_thumbnail(_alpha_png())
        assert thumb is not None
        with Image.open(io.BytesIO(thumb.read())) as out:
            assert out.mode == "RGB"
            assert max(out.size) <= 400

    def test_palette_png(self):
        """Mode "P" is promoted to RGBA before the resize.

        Pillow forces NEAREST resampling on palette images, so skipping the
        promotion visibly degrades the thumbnail.
        """
        thumb = generate_image_thumbnail(_palette_png())
        assert thumb is not None
        with Image.open(io.BytesIO(thumb.read())) as out:
            assert out.mode == "RGB"
            assert max(out.size) <= 400

    def test_cmyk_jpeg(self):
        source = _encode(Image.new("CMYK", (1200, 800), (10, 20, 30, 40)), "JPEG")
        thumb = generate_image_thumbnail(source)
        assert thumb is not None
        with Image.open(io.BytesIO(thumb.read())) as out:
            assert out.mode == "RGB"

    def test_preserves_aspect_ratio(self):
        thumb = generate_image_thumbnail(_jpeg(1200, 400))
        with Image.open(io.BytesIO(thumb.read())) as out:
            assert out.size == (400, 133)

    def test_raises_over_the_limit_rather_than_returning_none(self):
        """Returning None marked the asset COMPLETED with nothing in it.

        "Too large" is determinate and the user can act on it, so it has to
        reach ``process_media_asset``. Only "Pillow could not read this" stays
        a soft None.
        """
        with (
            override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000),
            self.assertRaises(ImageTooLargeError),
        ):
            generate_image_thumbnail(_alpha_png())

    def test_returns_none_on_a_file_that_is_not_an_image(self):
        assert generate_image_thumbnail(io.BytesIO(b"not an image at all")) is None


class ExtractImageMetadataTest(SimpleTestCase):
    def test_reports_real_dimensions_not_drafted_ones(self):
        assert extract_image_metadata(_jpeg(2400, 1600)) == {"width": 2400, "height": 1600}

    def test_reports_dimensions_even_over_the_limit(self):
        """Reading the header decodes nothing, so there is nothing to protect.

        Withholding these stored 0x0 on assets whose thumbnails generated
        perfectly well, because the thumbnail path drafts and this one does not.
        """
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
            assert extract_image_metadata(_alpha_png()) == {"width": 600, "height": 400}

    def test_agrees_with_the_thumbnail_path_on_a_large_jpeg(self):
        """The two must not judge the same file against different pixel counts.

        A 40MP JPEG drafts down to something cheap, so the thumbnail succeeds;
        metadata must not meanwhile decide the file is unusable and report 0x0.
        """
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=30_000_000):
            assert extract_image_metadata(_jpeg(8000, 5000)) == {"width": 8000, "height": 5000}
            assert generate_image_thumbnail(_jpeg(8000, 5000)) is not None

    def test_returns_empty_on_unreadable_input(self):
        assert extract_image_metadata(io.BytesIO(b"nope")) == {}


class ApplyImageEditsTest(SimpleTestCase):
    def test_no_operations_still_returns_a_file(self):
        """Regression: the save used to sit outside the open context.

        With no operations the working image IS the opened one, so leaving the
        context first closed the file pointer out from under ``save()``.
        """
        edited, size = apply_image_edits(_jpeg(800, 600), {})
        assert size == (800, 600)
        assert edited.size > 0

    def test_crop(self):
        edited, size = apply_image_edits(_jpeg(800, 600), {"crop": {"x": 10, "y": 20, "width": 100, "height": 50}})
        assert size == (100, 50)
        with Image.open(io.BytesIO(edited.read())) as out:
            assert out.size == (100, 50)

    def test_rotate_expands(self):
        _, size = apply_image_edits(_jpeg(800, 600), {"rotate": 90})
        assert size == (600, 800)

    def test_resize(self):
        _, size = apply_image_edits(_jpeg(800, 600), {"resize": {"width": 320, "height": 240}})
        assert size == (320, 240)

    def test_alpha_source_is_written_as_png(self):
        edited, _ = apply_image_edits(_alpha_png(), {"rotate": 180})
        assert edited.name.endswith(".png")

    def test_raises_over_the_limit(self):
        """Unlike the thumbnail path, this propagates: the edit has failed."""
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000), self.assertRaises(ImageTooLargeError):
            apply_image_edits(_alpha_png(), {"rotate": 90})


class UploadPixelValidationTest(SimpleTestCase):
    """The ceiling is enforced synchronously too, where the path allows it.

    Presigned direct-to-storage uploads never reach ``validate_file``, so the
    worker still has to enforce it — but for a normal upload, telling the user
    at submit time beats accepting the file and failing it minutes later with
    nothing on screen to explain why.
    """

    def _upload(self, data, name="image.png"):
        return SimpleUploadedFile(name, data, content_type="image/png")

    def test_rejects_an_image_over_the_pixel_limit(self):
        upload = self._upload(_alpha_png().getvalue())
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
            _, errors = validate_file(upload)
        assert any("megapixels" in e for e in errors)

    def test_the_message_names_the_dimensions_and_the_limit(self):
        upload = self._upload(_alpha_png().getvalue())
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
            _, errors = validate_file(upload)
        message = next(e for e in errors if "megapixels" in e)
        assert "600x400" in message
        assert "0.2 megapixels" in message
        assert "limit is 0.2" in message

    def test_accepts_a_large_jpeg_the_worker_can_handle(self):
        """Upload and worker must judge the same file the same way.

        Measuring raw header dimensions here rejected a 40MP JPEG that
        ``generate_image_thumbnail`` handles without trouble, because the JPEG
        decoder downscales during the read. That also made a REST upload behave
        differently from a presigned one, which never reaches this validator.
        """
        upload = SimpleUploadedFile("big.jpg", _jpeg(8000, 5000).getvalue(), content_type="image/jpeg")
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=30_000_000):
            file_type, errors = validate_file(upload)
            assert generate_image_thumbnail(_jpeg(8000, 5000)) is not None
        assert file_type == "image"
        assert errors == []

    def test_still_rejects_a_png_of_the_same_size(self):
        """PNG has no draft support, so it really would decode full-size."""
        upload = SimpleUploadedFile("big.png", _alpha_png(8000, 5000).getvalue(), content_type="image/png")
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=30_000_000):
            _, errors = validate_file(upload)
        assert any("megapixels" in e for e in errors)

    def test_accepts_an_image_under_the_limit(self):
        upload = self._upload(_alpha_png().getvalue())
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=1_000_000):
            file_type, errors = validate_file(upload)
        assert file_type == "image"
        assert errors == []

    def test_leaves_the_read_position_at_zero_for_the_caller(self):
        """The caller stores this file next; a consumed handle writes nothing."""
        upload = self._upload(_alpha_png().getvalue())
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=1_000_000):
            validate_file(upload)
        assert upload.tell() == 0

    def test_a_non_image_is_unaffected(self):
        upload = SimpleUploadedFile("clip.mp4", b"\x00\x00\x00\x20ftypmp42", content_type="video/mp4")
        with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=1):
            _, errors = validate_file(upload)
        assert not any("megapixels" in e for e in errors)
