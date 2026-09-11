from __future__ import annotations

from collections.abc import Awaitable, Callable
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
    CalResponseTooLargeError,
)

Transport = Callable[[CalRequest, CalClientConfig], Awaitable[CalResponse]]


def _install_transport(monkeypatch: pytest.MonkeyPatch, transport: Transport) -> None:
    def client_factory() -> CalHttpClient:
        return CalHttpClient(
            config=CalClientConfig(max_retries=0, retry_backoff_seconds=0),
            transport=transport,
        )

    monkeypatch.setattr(server_module, "CalHttpClient", client_factory)


def _assert_structured_error(
    result: object,
    *,
    kind: str,
    operation: str,
    upstream_reached: bool | None,
    retryable: bool,
    message: str,
    source_url: str | None = None,
    status_code: int | None = None,
) -> None:
    assert getattr(result, "is_error") is True
    expected = {
        "error": {
            "kind": kind,
            "operation": operation,
            "upstream_reached": upstream_reached,
            "retryable": retryable,
            "message": message,
            "source_url": source_url,
            "status_code": status_code,
        }
    }
    assert getattr(result, "structured_content") == expected
    content = getattr(result, "content")
    assert len(content) == 1
    assert isinstance(content[0], TextContent)
    assert kind in content[0].text
    assert message in content[0].text


@pytest.mark.anyio
async def test_local_validation_returns_structured_error_without_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal calls
        del request, config
        calls += 1
        raise AssertionError("local validation must not reach CAL transport")

    _install_transport(monkeypatch, transport)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_page", {"file_id": "not-a-cal-id"})

    _assert_structured_error(
        result,
        kind="invalid_input",
        operation="cal_text_page",
        upstream_reached=False,
        retryable=False,
        message="file_id must be a CAL decimal identifier",
    )
    assert calls == 0


@pytest.mark.anyio
async def test_sdk_argument_validation_returns_structured_invalid_input() -> None:
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_page", {"file_id": 123})

    assert result.is_error is True
    assert result.structured_content is not None
    error = result.structured_content["error"]
    assert error["kind"] == "invalid_input"
    assert error["operation"] == "cal_text_page"
    assert error["upstream_reached"] is False
    assert error["retryable"] is False
    assert error["source_url"] is None
    assert error["status_code"] is None
    assert "file_id" in error["message"]


@pytest.mark.anyio
async def test_parser_drift_returns_structured_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert request.path == "newsearchtxts.php"
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/newsearchtxts.php",
            body=b"<html><body>unrecognized successful markup</body></html>",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        )

    _install_transport(monkeypatch, transport)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_search", {"query": "Tel Dan"})

    _assert_structured_error(
        result,
        kind="parser_drift",
        operation="cal_text_search",
        upstream_reached=True,
        retryable=False,
        message="CAL text search page is missing its result marker",
    )
    rendered = " ".join(
        block.text for block in result.content if isinstance(block, TextContent)
    )
    assert "unrecognized successful markup" not in rendered


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "retryable"),
    ((503, True), (404, False)),
)
async def test_upstream_http_error_is_structured(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    retryable: bool,
) -> None:
    source_url = "https://cal.huc.edu/newsearchtxts.php?test=1"

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        return CalResponse(
            status_code=status_code,
            url=source_url,
            body=b"",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        )

    _install_transport(monkeypatch, transport)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_search", {"query": "Tel Dan"})

    _assert_structured_error(
        result,
        kind="upstream_http",
        operation="cal_text_search",
        upstream_reached=True,
        retryable=retryable,
        message=f"CAL returned HTTP {status_code} for {source_url}",
        source_url=source_url,
        status_code=status_code,
    )


@pytest.mark.anyio
async def test_network_failure_is_structured_without_guessing_reachability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        raise TimeoutError("transport-private detail")

    _install_transport(monkeypatch, transport)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_search", {"query": "Tel Dan"})

    _assert_structured_error(
        result,
        kind="network",
        operation="cal_text_search",
        upstream_reached=None,
        retryable=True,
        message="CAL request timeout",
    )
    assert "transport-private detail" not in str(result.content)


@pytest.mark.anyio
async def test_response_too_large_is_structured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_url = "https://cal.huc.edu/newsearchtxts.php"

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        raise CalResponseTooLargeError(source_url, 1024)

    _install_transport(monkeypatch, transport)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_search", {"query": "Tel Dan"})

    _assert_structured_error(
        result,
        kind="response_too_large",
        operation="cal_text_search",
        upstream_reached=True,
        retryable=False,
        message=f"CAL response exceeded configured 1024-byte limit for {source_url}",
        source_url=source_url,
    )


@pytest.mark.anyio
async def test_unexpected_programming_error_remains_sdk_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "DO_NOT_LEAK_PRIVATE_SENTINEL"

    async def crash(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError(secret)

    monkeypatch.setattr(server_module.TextService, "search", crash)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_search", {"query": "Tel Dan"})

    assert result.is_error is True
    assert result.structured_content is None
    texts = [block.text for block in result.content if isinstance(block, TextContent)]
    assert texts == ["Error executing tool cal_text_search"]
    assert secret not in str(result.content)


@pytest.mark.anyio
async def test_explicit_not_found_remains_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert request.path == "getlex.php"
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/getlex.php?coord=999999&word=0",
            body=b"<html><body>there is no data for this word</body></html>",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        )

    _install_transport(monkeypatch, transport)

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool(
            "cal_token_analysis",
            {"coordinate": "999999", "word_index": 0},
        )

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["status"] == "not_found"
    assert result.structured_content["candidates"] == []
