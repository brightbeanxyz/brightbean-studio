"""Unit tests for the opaque offset cursors shared by REST and MCP.

Both surfaces mint and accept the same cursor, so the parsing rules live
here rather than being re-asserted through each endpoint's tests. A cursor
is caller-supplied and trivially forgeable (base64 of plain JSON), so every
malformed shape must land on ``ValueError`` — the callers turn that into a
422 / INVALID_PARAMS, and anything unhandled would surface as a 500.
"""

from __future__ import annotations

import base64
import json

import pytest

from apps.api.pagination import decode_offset_cursor, encode_offset_cursor


def _cursor_for(payload) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()


class TestOffsetCursorRoundTrip:
    @pytest.mark.parametrize("offset", [0, 1, 20, 50, 999, 10_000])
    def test_round_trips(self, offset):
        assert decode_offset_cursor(encode_offset_cursor(offset)) == offset

    def test_absent_cursor_is_offset_zero(self):
        assert decode_offset_cursor(None) == 0
        assert decode_offset_cursor("") == 0


class TestOffsetCursorRejects:
    @pytest.mark.parametrize(
        "cursor",
        [
            "not-a-cursor",  # not base64
            "!!!!",  # base64 alphabet violation
            _cursor_for([1, 2, 3]),  # JSON, but not an object
            _cursor_for("5"),  # JSON string payload
            _cursor_for({"o": -1}),  # negative offset would slice backwards
            _cursor_for({"o": "5"}),  # string offset
            _cursor_for({"o": 1.5}),  # non-integer offset
            _cursor_for({"o": None}),
        ],
    )
    def test_malformed_cursor_raises_value_error(self, cursor):
        with pytest.raises(ValueError):
            decode_offset_cursor(cursor)

    def test_boolean_offset_is_rejected(self):
        """``bool`` is an ``int`` subclass — without the explicit guard,
        ``{"o": true}`` would silently page from offset 1.
        """
        with pytest.raises(ValueError):
            decode_offset_cursor(_cursor_for({"o": True}))

    def test_non_string_cursor_is_rejected(self):
        """MCP passes tool arguments through unvalidated by type in the
        handler-direct path; an int cursor must not reach ``.encode()``.
        """
        with pytest.raises(ValueError):
            decode_offset_cursor(5)  # type: ignore[arg-type]

    def test_payload_without_offset_key_defaults_to_zero(self):
        assert decode_offset_cursor(_cursor_for({})) == 0
