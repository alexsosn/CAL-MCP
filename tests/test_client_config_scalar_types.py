import pytest

import cal_mcp.client


_NUMERIC_FIELDS = (
    "connect_timeout_seconds",
    "read_timeout_seconds",
    "total_timeout_seconds",
    "retry_backoff_seconds",
    "cache_ttl_seconds",
)


@pytest.mark.parametrize("field", _NUMERIC_FIELDS)
@pytest.mark.parametrize("value", [True, False, "1", None])
def test_numeric_policy_fields_reject_boolean_and_non_numeric_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValueError, match=rf"^{field} must be a number$"):
        cal_mcp.client.CalClientConfig(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("connect_timeout_seconds", 1),
        ("connect_timeout_seconds", 1.5),
        ("read_timeout_seconds", 1),
        ("read_timeout_seconds", 1.5),
        ("total_timeout_seconds", 1),
        ("total_timeout_seconds", 1.5),
        ("retry_backoff_seconds", 0),
        ("retry_backoff_seconds", 0.5),
        ("cache_ttl_seconds", 1),
        ("cache_ttl_seconds", 1.5),
    ],
)
def test_numeric_policy_fields_preserve_valid_integer_and_float_inputs(
    field: str,
    value: int | float,
) -> None:
    config = cal_mcp.client.CalClientConfig(**{field: value})

    assert getattr(config, field) == value


@pytest.mark.parametrize("value", [0, 1, "true"])
def test_cache_enabled_requires_actual_boolean(value: object) -> None:
    with pytest.raises(ValueError, match=r"^cache_enabled must be a boolean$"):
        cal_mcp.client.CalClientConfig(cache_enabled=value)


@pytest.mark.parametrize("value", [True, False])
def test_cache_enabled_preserves_boolean_values(value: bool) -> None:
    config = cal_mcp.client.CalClientConfig(cache_enabled=value)

    assert config.cache_enabled is value


@pytest.mark.parametrize("value", [1, ["CAL-MCP"]])
def test_user_agent_requires_string(value: object) -> None:
    with pytest.raises(ValueError, match=r"^user_agent must be a string$"):
        cal_mcp.client.CalClientConfig(user_agent=value)


def test_user_agent_preserves_existing_empty_string_rule() -> None:
    with pytest.raises(ValueError, match=r"^user_agent must not be empty$"):
        cal_mcp.client.CalClientConfig(user_agent="   ")


def test_user_agent_accepts_non_empty_string() -> None:
    config = cal_mcp.client.CalClientConfig(user_agent="CAL-MCP/test")

    assert config.user_agent == "CAL-MCP/test"
