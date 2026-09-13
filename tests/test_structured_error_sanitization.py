from __future__ import annotations

import pytest

from cal_mcp.client import CalResponseTooLargeError, CalUpstreamError
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


@pytest.mark.parametrize(
    "error",
    [
        CalUpstreamError(503, "https://example.org/private?token=secret"),
        CalUpstreamError(503, "http://cal.huc.edu/private?token=secret"),
        CalResponseTooLargeError("https://example.org/private?token=secret", 1024),
    ],
)
def test_untrusted_exception_url_is_not_exposed(error: BaseException) -> None:
    classified = classify_public_tool_error("cal_text_search", error)

    assert classified is not None
    assert classified.source_url is None
    assert "example.org" not in classified.message
    assert "token=secret" not in classified.message
    assert "http://cal.huc.edu" not in classified.message
