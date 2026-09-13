from __future__ import annotations

from datetime import UTC, datetime

import pytest
from mcp import Client
from mcp.types import TextContent

import cal_mcp.server as server_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("body", "content_type", "expected_message"),
    [
        (
            b"{}",
            "application/json",
            "CAL returned unexpected content type 'application/json'",
        ),
        (
            b"<html><title>Maintenance</title><body>Please try later</body></html>",
            "text/html; charset=UTF-8",
            "CAL returned a probable maintenance page",
        ),
    ],
)
async def test_content_policy_errors_do_not_expose_untrusted_response_url(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
    content_type: str,
    expected_message: str,
) -> None:
    private_url = "https://example.org/private?token=DO_NOT_LEAK"

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        return CalResponse(
            status_code=200,
            url=private_url,
            body=body,
            content_type=content_type,
            retrieved_at=datetime(2026, 9, 13, tzinfo=UTC),
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
    assert error["source_url"] is None
    assert error["message"] == expected_message
    rendered = " ".join(block.text for block in result.content if isinstance(block, TextContent))
    assert "example.org" not in rendered
    assert "DO_NOT_LEAK" not in rendered
