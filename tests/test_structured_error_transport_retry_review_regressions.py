"""Adversarial MCP regression: non-retryable transport failures stay non-retryable."""

from __future__ import annotations

import pytest
from mcp import Client

import cal_mcp.server as server_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse


@pytest.mark.anyio
async def test_nonretryable_os_error_is_not_advertised_as_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal calls
        del request, config
        calls += 1
        raise OSError("DO_NOT_LEAK_PRIVATE_TRANSPORT_DETAIL")

    def client_factory() -> CalHttpClient:
        return CalHttpClient(
            config=CalClientConfig(max_retries=2, retry_backoff_seconds=0),
            transport=transport,
        )

    monkeypatch.setattr(server_module, "CalHttpClient", client_factory)
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_search", {"query": "Tel Dan"})

    assert calls == 1
    assert result.is_error is True
    assert result.structured_content is not None
    error = result.structured_content["error"]
    assert error["kind"] == "network"
    assert error["upstream_reached"] is None
    assert error["retryable"] is False
    assert error["message"] == "CAL non-retryable transport request failed"
    assert "DO_NOT_LEAK" not in str(result.content)
