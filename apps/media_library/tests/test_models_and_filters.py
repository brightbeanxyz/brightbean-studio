"""Tests for the Media Library app."""

import re
import uuid

from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase

from apps.common.templatetags.common_extras import json_attr
from apps.common.validators import MAX_TAG_LENGTH, MAX_TAGS, normalize_tags
from apps.media_library.models import MediaAsset


class MediaAssetModelTest(TestCase):
    """Test MediaAsset model properties."""

    def test_is_image(self):
        asset = MediaAsset()
        asset.media_type = MediaAsset.MediaType.IMAGE
        self.assertTrue(asset.is_image)
        self.assertFalse(asset.is_video)

    def test_is_video(self):
        asset = MediaAsset()
        asset.media_type = MediaAsset.MediaType.VIDEO
        self.assertTrue(asset.is_video)
        self.assertFalse(asset.is_image)

    def test_aspect_ratio(self):
        asset = MediaAsset()
        asset.width = 1920
        asset.height = 1080
        self.assertAlmostEqual(asset.aspect_ratio, 1.78, places=2)

    def test_aspect_ratio_none_when_no_dimensions(self):
        asset = MediaAsset()
        asset.width = 0
        asset.height = 0
        self.assertIsNone(asset.aspect_ratio)

    def test_file_size_display(self):
        asset = MediaAsset()
        asset.file_size = 1024
        self.assertIn("KB", asset.file_size_display)

        asset.file_size = 1048576
        self.assertIn("MB", asset.file_size_display)

        asset.file_size = 500
        self.assertIn("B", asset.file_size_display)

    def test_str_representation(self):
        asset = MediaAsset()
        asset.filename = "photo.jpg"
        self.assertEqual(str(asset), "photo.jpg")


class JsonAttrFilterTest(SimpleTestCase):
    """Test the json_attr template filter (attribute-context XSS guard)."""

    def test_escapes_script_payload(self):
        out = str(json_attr(["<script>alert(1)</script>", '"><img src=x>']))
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", out)
        self.assertIn("&quot;", out)
        self.assertNotIn("<script>", out)
        self.assertNotIn("<img", out)

    def test_none_returns_empty_array_literal(self):
        self.assertEqual(str(json_attr(None)), "[]")

    def test_empty_string_returns_empty_array_literal(self):
        # Django's string_if_invalid fallback for unresolved template
        # vars (e.g. `{{ post.tags }}` when `post is None`) renders as "".
        # That must not serialize to the JS string `""` — Alpine would
        # initialize `tags` as a string and break .push()/.includes().
        self.assertEqual(str(json_attr("")), "[]")

    def test_dict_is_serialized(self):
        out = str(json_attr({"a": 1, "b": "x"}))
        self.assertIn("&quot;a&quot;: 1", out)
        self.assertIn("&quot;b&quot;: &quot;x&quot;", out)
        self.assertNotIn('"a"', out)


class _StubAsset:
    def __init__(self, asset_id, tags, is_shared=False):
        self.id = asset_id
        self.tags = tags
        self.is_shared = is_shared


class _StubWorkspace:
    def __init__(self, workspace_id):
        self.id = workspace_id


class TagInputTemplateTest(SimpleTestCase):
    """Regression: malicious tag content must not break out of the x-data attribute."""

    def _render(self, tags):
        return render_to_string(
            "media_library/_tag_input.html",
            {
                "asset": _StubAsset(uuid.uuid4(), tags),
                "workspace": _StubWorkspace(uuid.uuid4()),
                "is_shared_library": False,
                "is_admin": False,
            },
        )

    def test_malicious_tag_is_escaped_in_x_data(self):
        rendered = self._render(['"><script>alert(1)</script>'])
        match = re.search(r'x-data="tagInput\(([^"]*)\)"', rendered)
        self.assertIsNotNone(match, 'x-data attribute should still be quoted with "')
        attr_body = match.group(1)
        self.assertIn("&lt;script&gt;", attr_body)
        self.assertIn("&quot;", attr_body)
        self.assertNotIn("<script>", attr_body)
        self.assertNotIn('"><script>', rendered)

    def test_empty_tags_renders_array_literal(self):
        rendered = self._render([])
        self.assertIn('x-data="tagInput([])"', rendered)


class NormalizeTagsTest(SimpleTestCase):
    """Validation contract for the tag-write endpoints."""

    def test_rejects_non_list(self):
        with self.assertRaises(ValueError):
            normalize_tags({"foo": "bar"})

    def test_rejects_too_many(self):
        with self.assertRaises(ValueError):
            normalize_tags(["x"] * (MAX_TAGS + 1))

    def test_accepts_at_limit(self):
        result = normalize_tags([f"tag{i}" for i in range(MAX_TAGS)])
        self.assertEqual(len(result), MAX_TAGS)

    def test_rejects_oversized(self):
        with self.assertRaises(ValueError):
            normalize_tags(["x" * (MAX_TAG_LENGTH + 1)])

    def test_rejects_non_string_element(self):
        with self.assertRaises(ValueError):
            normalize_tags([123])

    def test_strips_whitespace_and_dedupes(self):
        self.assertEqual(normalize_tags(["  a  ", "a", "b", "", "   "]), ["a", "b"])

    def test_preserves_malicious_payload_verbatim(self):
        payload = "<script>alert(1)</script>"
        self.assertEqual(normalize_tags([payload]), [payload])
