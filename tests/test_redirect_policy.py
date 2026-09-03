from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)


class RedirectTransport:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        self.calls += 1
        return CalResponse(
            status_code=302,
            url="https://cal.huc.edu/redirect.php",
            body=b"<html><body>redirect</body></html>",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        )


@pytest.mark.anyio
async def test_redirect_response_is_not_parsed_retried_or_cached() -> None:
    transport = RedirectTransport()
    client = CalHttpClient(
        config=CalClientConfig(max_retries=3, retry_backoff_seconds=0),
        transport=transport,
    )
    parser_calls = 0

    def parser(response: CalResponse) -> str:
        nonlocal parser_calls
        del response
        parser_calls += 1
        return "parsed"

    for _ in range(2):
        with pytest.raises(CalUpstreamError) as exc_info:
            await client.fetch(
                CalRequest(method="GET", path="entry.php"),
                parser=parser,
                cache_namespace="entry",
            )
        assert exc_info.value.status_code == 302

    assert parser_calls == 0
    assert transport.calls == 2
