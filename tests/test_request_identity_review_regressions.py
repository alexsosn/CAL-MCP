from __future__ import annotations

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


class CalRequestSubclass(CalRequest):
    pass


class PairContainerSubclass(tuple[tuple[str, str], ...]):
    pass


class StringPairSubclass(tuple[str, str]):
    pass


class StringSubclass(str):
    pass


async def unreachable_transport(
    request: CalRequest,
    config: CalClientConfig,
) -> CalResponse:
    del request, config
    raise AssertionError("invalid request must not reach transport")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("cal_request", "message"),
    [
        (
            CalRequest(
                method="DELETE",
                path="entry.php",
                params=cast(PairTuple, [("q", "one")]),
            ),
            "CAL requests must use GET or POST",
        ),
        (
            CalRequest(
                method="GET",
                path="https://example.org/entry.php",
                params=cast(PairTuple, [("q", "one")]),
            ),
            "CAL request path must be relative to cal.huc.edu",
        ),
        (
            CalRequest(
                method="GET",
                path="entry.php?q=one",
                params=cast(PairTuple, [("q", "one")]),
            ),
            "query parameters must be supplied via CalRequest.params",
        ),
        (
            CalRequest(
                method="GET",
                path="../entry.php",
                params=cast(PairTuple, [("q", "one")]),
            ),
            "CAL request path must stay within the CAL site",
        ),
    ],
)
async def test_method_and_path_boundary_errors_precede_pair_shape_errors(
    cal_request: CalRequest,
    message: str,
) -> None:
    client = CalHttpClient(transport=unreachable_transport)

    with pytest.raises(CalRequestValidationError, match=rf"^{message}$"):
        await client.fetch(
            cal_request,
            parser=lambda response: response.body,
            cache_namespace="entry",
        )


@pytest.mark.anyio
async def test_cal_request_subclass_is_rejected_before_transport() -> None:
    client = CalHttpClient(transport=unreachable_transport)

    with pytest.raises(
        CalRequestValidationError,
        match=r"^CAL request must be a CalRequest$",
    ):
        await client.fetch(
            CalRequestSubclass(method="GET", path="entry.php"),
            parser=lambda response: response.body,
            cache_namespace="entry",
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "params",
    [
        PairContainerSubclass((("q", "one"),)),
        (StringPairSubclass(("q", "one")),),
    ],
)
async def test_tuple_subclasses_are_rejected_as_mutable_identity_escape_hatches(
    params: PairTuple,
) -> None:
    client = CalHttpClient(transport=unreachable_transport)

    with pytest.raises(
        CalRequestValidationError,
        match=r"^CAL request params must be a tuple of string pairs$",
    ):
        await client.fetch(
            CalRequest(method="GET", path="entry.php", params=params),
            parser=lambda response: response.body,
            cache_namespace="entry",
        )


@pytest.mark.anyio
async def test_method_string_subclass_is_rejected_before_transport() -> None:
    client = CalHttpClient(transport=unreachable_transport)

    with pytest.raises(
        CalRequestValidationError,
        match=r"^CAL request method must be a string$",
    ):
        await client.fetch(
            CalRequest(method=StringSubclass("GET"), path="entry.php"),
            parser=lambda response: response.body,
            cache_namespace="entry",
        )


@pytest.mark.anyio
async def test_path_string_subclass_is_rejected_before_transport() -> None:
    client = CalHttpClient(transport=unreachable_transport)

    with pytest.raises(
        CalRequestValidationError,
        match=r"^CAL request path must be a string$",
    ):
        await client.fetch(
            CalRequest(method="GET", path=StringSubclass("entry.php")),
            parser=lambda response: response.body,
            cache_namespace="entry",
        )


@pytest.mark.anyio
async def test_namespace_string_subclass_is_rejected_before_transport() -> None:
    client = CalHttpClient(transport=unreachable_transport)

    with pytest.raises(
        CalRequestValidationError,
        match=r"^cache_namespace must be a string$",
    ):
        await client.fetch(
            CalRequest(method="GET", path="entry.php"),
            parser=lambda response: response.body,
            cache_namespace=StringSubclass("entry"),
        )


@pytest.mark.anyio
@pytest.mark.parametrize("field", ["params", "data"])
@pytest.mark.parametrize("member", ["key", "value"])
async def test_pair_string_subclasses_are_rejected_before_transport(
    field: str,
    member: str,
) -> None:
    client = CalHttpClient(transport=unreachable_transport)
    pairs = ((StringSubclass("q"), "one"),) if member == "key" else (("q", StringSubclass("one")),)
    request = (
        CalRequest(method="GET", path="entry.php", params=pairs)
        if field == "params"
        else CalRequest(method="POST", path="entry.php", data=pairs)
    )

    with pytest.raises(
        CalRequestValidationError,
        match=rf"^CAL request {field} must be a tuple of string pairs$",
    ):
        await client.fetch(
            request,
            parser=lambda response: response.body,
            cache_namespace="entry",
        )
