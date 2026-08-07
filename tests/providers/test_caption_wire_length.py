"""A caption is measured against the limit as the platform will receive it.

LinkedIn escapes reserved characters in the commentary it publishes, so a
2,990-character caption holding 20 parentheses arrives as 3,010 and is rejected
by the 3,000 limit. ``caption_wire_length`` is what the composer counts with, so
these tests hold it to what ``escape_commentary`` actually produces.
"""

from providers import CAPTION_ESCAPED_CHARS, caption_wire_length
from providers.linkedin import LINKEDIN_RESERVED_CHARS, escape_commentary


class TestMatchesTheEscapedPayload:
    """The counter and the payload must never disagree."""

    def test_agrees_with_escape_commentary(self):
        for platform in ("linkedin_personal", "linkedin_company"):
            for caption in (
                "",
                "plain text with no reserved characters",
                "Va al repo (contexto durable):\n- item",
                "#AI #Agents @someone [link](https://ex.com/a_b~c)",
                "a\\b",  # the backslash is escaped too
                LINKEDIN_RESERVED_CHARS,
                "\\" + LINKEDIN_RESERVED_CHARS * 3,
            ):
                assert caption_wire_length(platform, caption) == len(escape_commentary(caption)), (
                    f"{platform}: {caption!r}"
                )

    def test_every_escaped_char_costs_two(self):
        for ch in CAPTION_ESCAPED_CHARS["linkedin_personal"]:
            assert caption_wire_length("linkedin_personal", ch) == 2, ch

    def test_the_backslash_is_charged_for(self):
        # Absent from LINKEDIN_RESERVED_CHARS (escape_commentary handles it
        # separately), so it is easy to leave out of the wire cost.
        assert "\\" in CAPTION_ESCAPED_CHARS["linkedin_personal"]
        assert caption_wire_length("linkedin_personal", "a\\b") == 4


class TestPlatformsWithoutEscaping:
    def test_plain_platforms_count_the_typed_length(self):
        caption = "Look (here) #now"
        for platform in ("bluesky", "facebook", "instagram", "threads"):
            assert caption_wire_length(platform, caption) == len(caption)

    def test_unknown_platform_falls_back_to_len(self):
        assert caption_wire_length("some_new_platform", "Look (here)") == len("Look (here)")

    def test_empty_caption_is_zero_everywhere(self):
        assert caption_wire_length("linkedin_personal", "") == 0
        assert caption_wire_length("bluesky", "") == 0


class TestTheLimitItBuys:
    def test_a_caption_that_fits_unescaped_can_still_overflow(self):
        # The regression this exists to prevent: 2,990 typed characters, 20 of
        # them reserved, lands at 3,010 on the wire against a 3,000 limit.
        caption = "(" * 20 + "a" * 2970
        assert len(caption) == 2990
        assert caption_wire_length("linkedin_personal", caption) == 3010
