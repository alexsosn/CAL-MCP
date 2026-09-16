"""Independent review regression for the public SDK validation-message bound."""

from __future__ import annotations

from pydantic import ValidationError

from cal_mcp.errors import PublicErrorKind, PublicToolError
from cal_mcp.server import _sdk_validation_message


def test_sdk_validation_message_is_bounded_at_public_boundary() -> None:
    error = ValidationError.from_exception_data(
        "ToolArguments",
        [{"type": "missing", "loc": ("x" * 1000,), "input": {}}],
    )

    public_error = PublicToolError(
        kind=PublicErrorKind.INVALID_INPUT,
        operation="cal_text_page",
        upstream_reached=False,
        retryable=False,
        message=_sdk_validation_message(error),
    )

    assert public_error.message.startswith("Invalid tool arguments:")
    assert len(public_error.message) <= 500
    assert public_error.to_dict()["error"]["message"] == public_error.message
