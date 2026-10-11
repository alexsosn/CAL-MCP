"""Oversized integer CAL client config regression (#321). Offline-only."""

from __future__ import annotations

from typing import Any, cast

import pytest

from cal_mcp.client import CalClientConfig

_SCALAR_CONFIG_FIELDS = (
    "connect_timeout_seconds",
    "read_timeout_seconds",
    "total_timeout_seconds",
    "cache_ttl_seconds",
    "retry_backoff_seconds",
    "min_request_interval_seconds",
)


@pytest.mark.parametrize("field", _SCALAR_CONFIG_FIELDS)
def test_unrepresentable_integer_config_reports_field_specific_value_error(field: str) -> None:
    with pytest.raises(ValueError, match=rf"^{field} must be finite"):
        CalClientConfig(**cast(Any, {field: 10**1000}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("connect_timeout_seconds", 1),
        ("read_timeout_seconds", 1.5),
        ("total_timeout_seconds", 1),
        ("cache_ttl_seconds", 0.5),
        ("retry_backoff_seconds", 0),
        ("min_request_interval_seconds", 0),
        ("min_request_interval_seconds", 3.0),
    ],
)
def test_config_still_accepts_normal_integer_and_fractional_boundaries(
    field: str, value: int | float
) -> None:
    config = CalClientConfig(**cast(Any, {field: value}))
    assert getattr(config, field) == value
