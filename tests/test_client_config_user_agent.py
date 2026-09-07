from __future__ import annotations

import pytest

from cal_mcp.client import CalClientConfig


@pytest.mark.parametrize(
    "user_agent",
    [
        "CAL-MCP/0.1 λ",
        "CAL-MCP/0.1\nX-Test: value",
        "CAL-MCP/0.1\rX-Test: value",
        "CAL-MCP/0.1\tX-Test: value",
        "CAL-MCP/0.1\x00X",
        "CAL-MCP/0.1\x7fX",
    ],
)
def test_user_agent_rejects_non_printable_or_non_ascii_characters(user_agent: str) -> None:
    with pytest.raises(
        ValueError,
        match="user_agent must contain only printable ASCII characters",
    ):
        CalClientConfig(user_agent=user_agent)


def test_user_agent_default_remains_printable_ascii() -> None:
    user_agent = CalClientConfig().user_agent

    assert user_agent.startswith("CAL-MCP/")
    assert all(0x20 <= ord(char) <= 0x7E for char in user_agent)


@pytest.mark.parametrize(
    "user_agent",
    [
        "CAL-MCP-test/1.0 (+https://example.org)",
        "CAL MCP test client",
        " ~",
    ],
)
def test_user_agent_accepts_non_empty_printable_ascii(user_agent: str) -> None:
    assert CalClientConfig(user_agent=user_agent).user_agent == user_agent


def test_user_agent_preserves_existing_type_and_empty_validation_precedence() -> None:
    with pytest.raises(ValueError, match="user_agent must be a string"):
        CalClientConfig(user_agent=123)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="user_agent must not be empty"):
        CalClientConfig(user_agent=" \t ")
