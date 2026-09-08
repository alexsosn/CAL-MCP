from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRequest,
    CalRequestValidationError,
    CalResponse,
)

PairTuple = tuple[tuple[str, str], ...]


class RecordingTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/entry.php",
            body=b"<html><body>ok</body></html>",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
        )


def parse_text(response: CalResponse) -> str:
    return response.body.decode()


def request_with_pair_field(field: str, value: object) -> CalRequest:
    typed_value = cast(PairTuple, value)
    if field == "params":
        return CalRequest(method="GET", path="entry.php", params=typed_value)
    if field == "data":
        return CalRequest(method="POST", path="entry.php", data=typed_value)
    raise AssertionError(f"unexpected field {field}")


@pytest.mark.anyio
async def test_non_cal_request_is_rejected_before_transport() -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)
    request = cast(CalRequest, object())

    with pytest.raises(
        CalRequestValidationError,
        match=r"^CAL request must be a CalRequest$",
    ):
        await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert transport.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("method", 1, "CAL request method must be a string"),
        ("path", None, "CAL request path must be a string"),
    ],
)
async def test_request_scalar_runtime_types_are_rejected_before_transport(
    field: str,
    value: object,
    message: str,
) -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)
    if field == "method":
        request = CalRequest(method=cast(str, value), path="entry.php")
    else:
        request = CalRequest(method="GET", path=cast(str, value))

    with pytest.raises(CalRequestValidationError, match=rf"^{message}$"):
        await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert transport.requests == []


@pytest.mark.anyio
async def test_cache_namespace_runtime_type_is_rejected_before_transport() -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)

    with pytest.raises(
        CalRequestValidationError,
        match=r"^cache_namespace must be a string$",
    ):
        await client.fetch(
            CalRequest(method="GET", path="entry.php"),
            parser=parse_text,
            cache_namespace=cast(str, 1),
        )

    assert transport.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize("field", ["params", "data"])
@pytest.mark.parametrize(
    "value",
    [
        [("q", "one")],
        (["q", "one"],),
        (("q",),),
        (("q", "one", "extra"),),
        ((1, "one"),),
        (("q", 1),),
    ],
)
async def test_request_pair_fields_require_immutable_two_string_tuples(
    field: str,
    value: object,
) -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)
    request = request_with_pair_field(field, value)

    with pytest.raises(
        CalRequestValidationError,
        match=rf"^CAL request {field} must be a tuple of string pairs$",
    ):
        await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert transport.requests == []


@pytest.mark.anyio
async def test_valid_request_identity_preserves_normalization_and_repeated_pair_order() -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)
    params = (("q", "one"), ("q", "two"))
    data = (("field", "alpha"), ("field", "beta"))

    result = await client.fetch(
        CalRequest(
            method=" get ",
            path="/entry.php",
            params=params,
            data=data,
        ),
        parser=parse_text,
        cache_namespace="entry",
    )

    assert result.value == "<html><body>ok</body></html>"
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="entry.php",
            params=params,
            data=data,
        )
    ]
    assert transport.requests[0].params is params
    assert transport.requests[0].data is data


@pytest.mark.anyio
async def test_empty_pair_tuples_remain_valid() -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)

    await client.fetch(
        CalRequest(method="GET", path="entry.php", params=(), data=()),
        parser=parse_text,
        cache_namespace="entry",
    )

    assert transport.requests == [CalRequest(method="GET", path="entry.php")]


@pytest.mark.anyio
async def test_whitespace_empty_cache_namespace_keeps_existing_error() -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)

    with pytest.raises(
        CalRequestValidationError,
        match=r"^cache_namespace must not be empty$",
    ):
        await client.fetch(
            CalRequest(method="GET", path="entry.php"),
            parser=parse_text,
            cache_namespace="   ",
        )

    assert transport.requests == []
