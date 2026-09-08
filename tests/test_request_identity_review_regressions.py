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


async def unreachable_transport(
    request: CalRequest,
    config: CalClientConfig,
) -> CalResponse:
    del request, config
    raise AssertionError("invalid request must not reach transport")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("request", "message"),
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
    request: CalRequest,
    message: str,
) -> None:
    client = CalHttpClient(transport=unreachable_transport)

    with pytest.raises(CalRequestValidationError, match=rf"^{message}$"):
        await client.fetch(request, parser=lambda response: response.body, cache_namespace="entry")
