"""Adversarial regressions against public structured-error disclosure paths."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from mcp import Client
from mcp.types import TextContent

import cal_mcp.server as server_module
from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)
from cal_mcp.errors import classify_public_tool_error


@pytest.mark.anyio
@pytest.mark.parametrize(
    "content_type",
    [
        "application/json; boundary=DO_NOT_LEAK",
        "application/DO_NOT_LEAK",
    ],
)
async def test_untrusted_content_type_is_not_public(
    monkeypatch: pytest.MonkeyPatch, content_type: str
) -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/search.php",
            body=b"{}",
            content_type=content_type,
            retrieved_at=datetime(2026, 9, 16, tzinfo=UTC),
        )

    def client_factory() -> CalHttpClient:
        return CalHttpClient(
            config=CalClientConfig(max_retries=0, retry_backoff_seconds=0),
            transport=transport,
        )

    monkeypatch.setattr(server_module, "CalHttpClient", client_factory)
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_search", {"query": "Tel Dan"})

    assert result.is_error is True
    assert result.structured_content is not None
    error = result.structured_content["error"]
    assert error["kind"] == "content"
    assert "DO_NOT_LEAK" not in error["message"]
    rendered = " ".join(block.text for block in result.content if isinstance(block, TextContent))
    assert "DO_NOT_LEAK" not in rendered


def test_url_with_control_characters_is_never_a_trusted_source() -> None:
    error = CalUpstreamError(503, "https://cal.huc.edu/search.php\nDO_NOT_LEAK")
    classified = classify_public_tool_error("cal_text_search", error)
    assert classified is not None
    assert classified.source_url is None
    assert "DO_NOT_LEAK" not in classified.message
