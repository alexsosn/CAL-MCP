from __future__ import annotations

from typing import Any, cast

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.search import EnglishSearchService


class RejectingTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        raise AssertionError("invalid specialized field reached CAL transport")


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_field", ["unknown", "alchemy ", "(alchem"])
async def test_invalid_specialized_gloss_field_is_rejected_before_transport(
    invalid_field: str,
) -> None:
    transport = RejectingTransport()
    service = EnglishSearchService(CalHttpClient(transport=transport))
    search_field = getattr(service, "search_gloss_field", None)
    assert callable(search_field)

    with pytest.raises(ValueError, match="unsupported CAL specialized gloss field"):
        await search_field(cast(Any, invalid_field))

    assert transport.requests == []
