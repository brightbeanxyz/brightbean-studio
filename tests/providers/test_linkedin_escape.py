"""Tests for LinkedIn commentary escaping (reserved little-text characters).

LinkedIn's Posts API silently truncates ``commentary`` at the first unescaped
reserved character (e.g. a ``(`` drops everything after it), which published
posts as just their first sentence. ``_escape_commentary`` prefixes each
reserved char with a backslash so the full text renders.
"""

from providers.linkedin import LinkedInProvider, _escape_commentary

RESERVED = set("|{}@[]()<>#*_~")


class TestEscapeCommentary:
    def test_escapes_reserved_characters(self):
        assert _escape_commentary("(a)") == "\\(a\\)"
        assert _escape_commentary("pre_commands") == "pre\\_commands"
        assert _escape_commentary("#AI #Agents") == "\\#AI \\#Agents"
        assert _escape_commentary("{{x}}") == "\\{\\{x\\}\\}"
        assert _escape_commentary("a*b~c<d>e|f@g[h]i") == "a\\*b\\~c\\<d\\>e\\|f\\@g\\[h\\]i"

    def test_escapes_backslash_first(self):
        # A literal backslash is doubled exactly once (not compounded with the
        # escapes we add afterwards).
        assert _escape_commentary("a\\b") == "a\\\\b"

    def test_leaves_plain_text_and_urls_untouched(self):
        assert _escape_commentary("Hola mundo, ¿qué tal?") == "Hola mundo, ¿qué tal?"
        url = "https://dev.to/agentprojectcontext/mcp-scopes-are-trust-boundaries-not-settings-2i18"
        assert _escape_commentary(url) == url

    def test_empty_and_none_are_safe(self):
        assert _escape_commentary("") == ""
        assert _escape_commentary(None) is None

    def test_no_unescaped_reserved_char_remains(self):
        # Regression: this caption published on LinkedIn as only "Va al repo ".
        caption = "Va al repo (contexto durable y portable):\n- item"
        out = _escape_commentary(caption)
        for i, ch in enumerate(out):
            if ch in RESERVED:
                assert i > 0 and out[i - 1] == "\\", f"unescaped {ch!r} at index {i}"


class TestBuildPostBodyEscapes:
    def test_commentary_in_body_is_escaped(self):
        provider = LinkedInProvider.__new__(LinkedInProvider)
        body = provider._build_post_body("urn:li:person:abc", "Va al repo (durable)")
        assert body["commentary"] == "Va al repo \\(durable\\)"
        assert body["author"] == "urn:li:person:abc"
