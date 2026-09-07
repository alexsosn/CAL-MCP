from __future__ import annotations

from typing import Any, cast

import pytest

from cal_mcp.client import CalClientConfig


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_concurrency", 1.5),
        ("max_concurrency", "2"),
        ("max_concurrency", True),
        ("max_concurrency", False),
        ("max_retries", 1.5),
        ("max_retries", "1"),
        ("max_retries", True),
        ("max_retries", False),
        ("cache_max_entries", 1.5),
        ("cache_max_entries", "128"),
        ("cache_max_entries", True),
        ("cache_max_entries", False),
    ],
)
def test_count_policy_fields_reject_non_integer_and_boolean_values(
    field: str,
    value: object,
) -> None:
    kwargs = cast(Any, {field: value})

    with pytest.raises(ValueError, match=rf"^{field} must be an integer$"):
        CalClientConfig(**kwargs)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_concurrency", 1),
        ("max_concurrency", 8),
        ("max_retries", 0),
        ("max_retries", 3),
        ("cache_max_entries", 0),
        ("cache_max_entries", 4096),
    ],
)
def test_count_policy_integer_boundaries_remain_valid(field: str, value: int) -> None:
    kwargs = cast(Any, {field: value})
    config = CalClientConfig(**kwargs)

    assert getattr(config, field) == value


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("max_concurrency", 0, "max_concurrency must be between 1 and 8"),
        ("max_concurrency", 9, "max_concurrency must be between 1 and 8"),
        ("max_retries", -1, "max_retries must be between 0 and 3"),
        ("max_retries", 4, "max_retries must be between 0 and 3"),
        ("cache_max_entries", -1, "cache_max_entries must be between 0 and 4096"),
        ("cache_max_entries", 4097, "cache_max_entries must be between 0 and 4096"),
    ],
)
def test_count_policy_out_of_range_integer_errors_remain_stable(
    field: str,
    value: int,
    message: str,
) -> None:
    kwargs = cast(Any, {field: value})

    with pytest.raises(ValueError, match=rf"^{message}$"):
        CalClientConfig(**kwargs)


_NUMERIC_SCALAR_FIELDS = (
    "connect_timeout_seconds",
    "read_timeout_seconds",
    "total_timeout_seconds",
    "retry_backoff_seconds",
    "cache_ttl_seconds",
)


@pytest.mark.parametrize("field", _NUMERIC_SCALAR_FIELDS)
@pytest.mark.parametrize("value", [True, False, "1", None])
def test_numeric_scalar_fields_reject_boolean_and_non_numeric_values(
    field: str,
    value: object,
) -> None:
    kwargs = cast(Any, {field: value})

    with pytest.raises(ValueError, match=rf"^{field} must be a number$"):
        CalClientConfig(**kwargs)


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
def test_numeric_scalar_fields_preserve_valid_integer_and_float_inputs(
    field: str,
    value: int | float,
) -> None:
    kwargs = cast(Any, {field: value})
    config = CalClientConfig(**kwargs)

    assert getattr(config, field) == value


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "connect_timeout_seconds",
            float("nan"),
            "connect_timeout_seconds must be finite and > 0",
        ),
        (
            "read_timeout_seconds",
            float("inf"),
            "read_timeout_seconds must be finite and > 0",
        ),
        (
            "total_timeout_seconds",
            float("-inf"),
            "total_timeout_seconds must be finite and > 0",
        ),
        (
            "cache_ttl_seconds",
            float("nan"),
            "cache_ttl_seconds must be finite and > 0",
        ),
        (
            "retry_backoff_seconds",
            float("inf"),
            "retry_backoff_seconds must be finite and between 0 and 1",
        ),
        (
            "retry_backoff_seconds",
            float("nan"),
            "retry_backoff_seconds must be finite and between 0 and 1",
        ),
    ],
)
def test_numeric_scalar_non_finite_errors_remain_stable(
    field: str,
    value: float,
    message: str,
) -> None:
    kwargs = cast(Any, {field: value})

    with pytest.raises(ValueError, match=rf"^{message}$"):
        CalClientConfig(**kwargs)


@pytest.mark.parametrize("value", [0, 1, "true"])
def test_cache_enabled_requires_actual_boolean(value: object) -> None:
    with pytest.raises(ValueError, match=r"^cache_enabled must be a boolean$"):
        CalClientConfig(cache_enabled=cast(Any, value))


@pytest.mark.parametrize("value", [True, False])
def test_cache_enabled_preserves_boolean_values(value: bool) -> None:
    config = CalClientConfig(cache_enabled=value)

    assert config.cache_enabled is value


@pytest.mark.parametrize("value", [1, ["CAL-MCP"]])
def test_user_agent_requires_string(value: object) -> None:
    with pytest.raises(ValueError, match=r"^user_agent must be a string$"):
        CalClientConfig(user_agent=cast(Any, value))


def test_user_agent_preserves_existing_empty_string_rule() -> None:
    with pytest.raises(ValueError, match=r"^user_agent must not be empty$"):
        CalClientConfig(user_agent="   ")


def test_user_agent_accepts_non_empty_string() -> None:
    config = CalClientConfig(user_agent="CAL-MCP/test")

    assert config.user_agent == "CAL-MCP/test"
