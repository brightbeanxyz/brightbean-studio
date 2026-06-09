"""Tests for apps.common.validators."""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.common.validators import (
    MAX_TAG_LENGTH,
    MAX_TAGS,
    MAX_YT_TAG_LENGTH,
    MAX_YT_TAGS_TOTAL_CHARS,
    is_safe_url,
    normalize_tags,
    parse_and_truncate_tag_string,
    parse_and_truncate_youtube_tag_string,
)


def _fake_addrinfo(ip):
    return [(0, 0, 0, "", (ip, 0))]


class NormalizeTagsTest(SimpleTestCase):
    """Strict normalization for JSON API endpoints."""

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


class ParseAndTruncateTagStringTest(SimpleTestCase):
    """Lenient normalization for HTML form POSTs — silently truncates."""

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(parse_and_truncate_tag_string(""), [])

    def test_whitespace_only_returns_empty_list(self):
        self.assertEqual(parse_and_truncate_tag_string("   ,  ,  "), [])

    def test_strips_and_dedupes(self):
        self.assertEqual(parse_and_truncate_tag_string("  a, a, b, ,c"), ["a", "b", "c"])

    def test_truncates_count_to_max_tags(self):
        raw = ",".join(f"tag{i}" for i in range(MAX_TAGS + 5))
        out = parse_and_truncate_tag_string(raw)
        self.assertEqual(len(out), MAX_TAGS)
        self.assertEqual(out[0], "tag0")
        self.assertEqual(out[-1], f"tag{MAX_TAGS - 1}")

    def test_truncates_overlong_tag(self):
        long_tag = "x" * (MAX_TAG_LENGTH + 50)
        out = parse_and_truncate_tag_string(long_tag)
        self.assertEqual(out, ["x" * MAX_TAG_LENGTH])

    def test_preserves_malicious_payload_verbatim(self):
        # Server-side normalization does NOT escape — render-time escape is the
        # security boundary. The string should round-trip unchanged into storage.
        payload = "<script>alert(1)</script>"
        self.assertEqual(parse_and_truncate_tag_string(payload), [payload])


class ParseAndTruncateYoutubeTagStringTest(SimpleTestCase):
    """YouTube-specific cap: total-chars across all tags <= 500."""

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(parse_and_truncate_youtube_tag_string(""), [])

    def test_caps_each_tag_at_yt_length(self):
        long_tag = "y" * (MAX_YT_TAG_LENGTH + 10)
        out = parse_and_truncate_youtube_tag_string(long_tag)
        self.assertEqual(out, ["y" * MAX_YT_TAG_LENGTH])

    def test_caps_total_chars(self):
        # 11 tags of MAX_YT_TAG_LENGTH chars each = 11*50 + 10 delimiters = 560 > 500
        # Should truncate to fit within MAX_YT_TAGS_TOTAL_CHARS
        tag = "z" * MAX_YT_TAG_LENGTH
        raw = ",".join(f"{tag}{i}" for i in range(20))
        out = parse_and_truncate_youtube_tag_string(raw)
        # Each output tag is 50 chars (since YT cap clips to 50)
        # Delimiter cost = len(out) - 1 (between tags)
        total_chars = sum(len(t) for t in out) + max(0, len(out) - 1)
        self.assertLessEqual(total_chars, MAX_YT_TAGS_TOTAL_CHARS)

    def test_dedupes(self):
        self.assertEqual(parse_and_truncate_youtube_tag_string("a, a, b, a"), ["a", "b"])

    def test_strips_whitespace(self):
        self.assertEqual(parse_and_truncate_youtube_tag_string("  a  ,  b  "), ["a", "b"])


class IsSafeUrlTest(SimpleTestCase):
    """SSRF guard: reject non-http(s) and private/reserved IPs."""

    def test_rejects_file_scheme(self):
        self.assertFalse(is_safe_url("file:///etc/passwd"))

    def test_rejects_gopher_scheme(self):
        self.assertFalse(is_safe_url("gopher://example.com/"))

    def test_rejects_javascript_scheme(self):
        self.assertFalse(is_safe_url("javascript:alert(1)"))

    def test_rejects_empty_hostname(self):
        self.assertFalse(is_safe_url("http:///path"))

    def test_rejects_malformed(self):
        self.assertFalse(is_safe_url("not a url"))

    @patch("socket.getaddrinfo")
    def test_rejects_loopback_ipv4(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("127.0.0.1")
        self.assertFalse(is_safe_url("http://localhost/"))

    @patch("socket.getaddrinfo")
    def test_rejects_loopback_ipv6(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("::1")
        self.assertFalse(is_safe_url("http://ip6-localhost/"))

    @patch("socket.getaddrinfo")
    def test_rejects_private_10(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("10.0.0.5")
        self.assertFalse(is_safe_url("http://internal.example.com/"))

    @patch("socket.getaddrinfo")
    def test_rejects_link_local_metadata(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("169.254.169.254")
        self.assertFalse(is_safe_url("http://metadata.example.com/"))

    @patch("socket.getaddrinfo")
    def test_rejects_private_172(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("172.16.5.5")
        self.assertFalse(is_safe_url("http://internal.example.com/"))

    @patch("socket.getaddrinfo")
    def test_rejects_private_192(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("192.168.1.1")
        self.assertFalse(is_safe_url("http://router.example.com/"))

    @patch("socket.getaddrinfo")
    def test_rejects_dns_rebind_with_any_private_address(self, mock_getaddrinfo):
        # Hostname resolves to BOTH a public and a private IP; must reject.
        mock_getaddrinfo.return_value = [
            (0, 0, 0, "", ("8.8.8.8", 0)),
            (0, 0, 0, "", ("10.0.0.1", 0)),
        ]
        self.assertFalse(is_safe_url("http://malicious-rebind.example.com/"))

    @patch("socket.getaddrinfo")
    def test_accepts_public_https(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("8.8.8.8")
        self.assertTrue(is_safe_url("https://example.com/feed.xml"))

    @patch("socket.getaddrinfo")
    def test_accepts_public_http(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _fake_addrinfo("93.184.216.34")
        self.assertTrue(is_safe_url("http://example.com/"))


class ValidateHexColorTest(SimpleTestCase):
    """Hex-color validator: 6-digit #RRGGBB or empty only."""

    def test_accepts_lowercase_hex(self):
        from apps.common.validators import validate_hex_color

        validate_hex_color("#3b82f6")

    def test_accepts_uppercase_hex(self):
        from apps.common.validators import validate_hex_color

        validate_hex_color("#3B82F6")

    def test_accepts_empty_string(self):
        from apps.common.validators import validate_hex_color

        validate_hex_color("")

    def test_accepts_none(self):
        from apps.common.validators import validate_hex_color

        validate_hex_color(None)

    def test_rejects_css_injection_attempt(self):
        from django.core.exceptions import ValidationError

        from apps.common.validators import validate_hex_color

        with self.assertRaises(ValidationError):
            validate_hex_color("red;background:url(//evil)")

    def test_rejects_three_digit_short_form(self):
        from django.core.exceptions import ValidationError

        from apps.common.validators import validate_hex_color

        with self.assertRaises(ValidationError):
            validate_hex_color("#f00")

    def test_rejects_color_name(self):
        from django.core.exceptions import ValidationError

        from apps.common.validators import validate_hex_color

        with self.assertRaises(ValidationError):
            validate_hex_color("red")

    def test_rejects_alpha_channel(self):
        from django.core.exceptions import ValidationError

        from apps.common.validators import validate_hex_color

        with self.assertRaises(ValidationError):
            validate_hex_color("#3B82F6FF")


class SafeXmlFromStringTest(SimpleTestCase):
    """XML hardening: bound size, reject DTD/entity declarations."""

    def test_parses_normal_rss(self):
        from apps.common.validators import safe_xml_fromstring

        body = b"<?xml version='1.0'?><rss><channel><title>OK</title></channel></rss>"
        root = safe_xml_fromstring(body)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, "rss")

    def test_rejects_billion_laughs(self):
        from apps.common.validators import safe_xml_fromstring

        body = (
            b"<?xml version='1.0'?>"
            b"<!DOCTYPE lolz ["
            b"  <!ENTITY lol 'lol'>"
            b"  <!ENTITY lol2 '&lol;&lol;&lol;'>"
            b"]>"
            b"<lolz>&lol2;</lolz>"
        )
        self.assertIsNone(safe_xml_fromstring(body))

    def test_rejects_doctype_alone(self):
        from apps.common.validators import safe_xml_fromstring

        body = b"<?xml version='1.0'?><!DOCTYPE feed><rss/>"
        self.assertIsNone(safe_xml_fromstring(body))

    def test_rejects_oversized(self):
        from apps.common.validators import safe_xml_fromstring

        body = b"<rss>" + b"x" * (6 * 1024 * 1024) + b"</rss>"
        self.assertIsNone(safe_xml_fromstring(body))

    def test_rejects_str_input(self):
        # The helper takes bytes only — callers must encode first.
        from apps.common.validators import safe_xml_fromstring

        self.assertIsNone(safe_xml_fromstring("<rss/>"))

    def test_rejects_malformed_xml(self):
        from apps.common.validators import safe_xml_fromstring

        self.assertIsNone(safe_xml_fromstring(b"<rss><channel></rss>"))
