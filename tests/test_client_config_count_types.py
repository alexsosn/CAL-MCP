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
