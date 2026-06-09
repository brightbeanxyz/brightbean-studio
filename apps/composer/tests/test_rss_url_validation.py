"""Tests for the RSS feed URL validator (SSRF guard + redirect handling)."""

from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.composer.views import _validate_rss_url

_VALID_RSS = b"""<?xml version='1.0'?><rss version='2.0'><channel>
<title>Sample</title><link>https://example.com</link></channel></rss>"""


def _public_addrinfo(*_args, **_kwargs):
    return [(0, 0, 0, "", ("8.8.8.8", 0))]


def _private_addrinfo(*_args, **_kwargs):
    return [(0, 0, 0, "", ("10.0.0.1", 0))]


class ValidateRssUrlTests(SimpleTestCase):
    def test_rejects_private_ip_url(self):
        with patch("socket.getaddrinfo", side_effect=_private_addrinfo):
            ok, err, meta = _validate_rss_url("http://internal.example.com/feed")
        self.assertFalse(ok)
        self.assertIn("Could not reach", err)
        self.assertEqual(meta, {})

    def test_rejects_file_scheme_url(self):
        ok, err, _ = _validate_rss_url("file:///etc/passwd")
        self.assertFalse(ok)
        self.assertIn("Could not reach", err)

    def test_follows_absolute_redirect_to_public_host(self):
        with patch("socket.getaddrinfo", side_effect=_public_addrinfo):
            responses = [
                Mock(status_code=302, headers={"Location": "https://feeds.example.com/rss.xml"}, content=b""),
                Mock(status_code=200, headers={}, content=_VALID_RSS),
            ]
            with patch("httpx.get", side_effect=responses) as httpx_get:
                ok, err, _ = _validate_rss_url("https://example.com/feed")
            self.assertTrue(ok, msg=err)
            self.assertEqual(httpx_get.call_count, 2)

    def test_resolves_relative_redirect_location(self):
        """A redirect with `Location: /feed.xml` must resolve against the request URL."""
        with patch("socket.getaddrinfo", side_effect=_public_addrinfo):
            responses = [
                Mock(status_code=302, headers={"Location": "/feed.xml"}, content=b""),
                Mock(status_code=200, headers={}, content=_VALID_RSS),
            ]
            with patch("httpx.get", side_effect=responses) as httpx_get:
                ok, err, _ = _validate_rss_url("https://example.com/blog")
            self.assertTrue(ok, msg=err)
            # Second call must use the absolute resolved URL.
            second_call_url = httpx_get.call_args_list[1].args[0]
            self.assertEqual(second_call_url, "https://example.com/feed.xml")

    def test_resolves_scheme_relative_redirect_location(self):
        """`Location: //feeds.example.com/rss.xml` must resolve via the original scheme."""
        with patch("socket.getaddrinfo", side_effect=_public_addrinfo):
            responses = [
                Mock(status_code=301, headers={"Location": "//feeds.example.com/rss.xml"}, content=b""),
                Mock(status_code=200, headers={}, content=_VALID_RSS),
            ]
            with patch("httpx.get", side_effect=responses) as httpx_get:
                ok, err, _ = _validate_rss_url("https://example.com/feed")
            self.assertTrue(ok, msg=err)
            second_call_url = httpx_get.call_args_list[1].args[0]
            self.assertEqual(second_call_url, "https://feeds.example.com/rss.xml")

    def test_rejects_redirect_to_private_ip(self):
        """A 302 → http://127.0.0.1 must be blocked at the validator."""
        public_then_private = iter(
            [
                [(0, 0, 0, "", ("8.8.8.8", 0))],  # initial public host
                [(0, 0, 0, "", ("127.0.0.1", 0))],  # redirect target
            ]
        )
        with patch("socket.getaddrinfo", side_effect=lambda *a, **k: next(public_then_private)):
            response = Mock(status_code=302, headers={"Location": "http://localhost/admin"}, content=b"")
            with patch("httpx.get", return_value=response):
                ok, err, _ = _validate_rss_url("https://example.com/feed")
        self.assertFalse(ok)
        self.assertIn("Could not reach", err)
