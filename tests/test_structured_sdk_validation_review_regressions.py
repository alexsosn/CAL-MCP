"""Independent review regression for the public SDK validation-message bound."""

from __future__ import annotations

from pydantic import ValidationError

from cal_mcp.server import _sdk_validation_message


def test_sdk_validation_message_is_bounded_for_long_field_locations() -> None:
    error = ValidationError.from_exception_data(
        "ToolArguments",
        [{"type": "missing", "loc": ("x" * 1000,), "input": {}}],
    )

    message = _sdk_validation_message(error)

    assert message.startswith("Invalid tool arguments:")
    assert len(message) <= 500
