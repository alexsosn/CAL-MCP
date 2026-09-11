from __future__ import annotations

from cal_mcp.errors import CalInputError, PublicErrorKind, classify_public_tool_error


def test_public_error_message_is_one_line_and_bounded() -> None:
    error = CalInputError("  first line\nsecond line  " + ("x" * 600))

    classified = classify_public_tool_error("cal_text_page", error)

    assert classified is not None
    assert classified.kind is PublicErrorKind.INVALID_INPUT
    assert classified.upstream_reached is False
    assert classified.retryable is False
    assert "\n" not in classified.message
    assert classified.message.startswith("first line second line ")
    assert len(classified.message) == 500
