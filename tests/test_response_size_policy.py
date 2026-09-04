from __future__ import annotations

from collections.abc import AsyncIterator

import httpx2
import pytest

import cal_mcp.client as client_module
from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRequest,
    CalResponse,
    CalResponseTooLargeError,
)


class CountingStream(httpx2.AsyncByteStream):
    def __init__(self, chunks: tuple[bytes, ...]) -> None:
        self.chunks = chunks
        self.yielded = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            self.yielded += 1
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


def patch_httpx2_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: object,
) -> None:
    real_async_client = httpx2.AsyncClient
    mock_transport = httpx2.MockTransport(handler)  # type: ignore[arg-type]

    def async_client_factory(**kwargs: object) -> httpx2.AsyncClient:
        return real_async_client(transport=mock_transport, **kwargs)

    monkeypatch.setattr(client_module.httpx2, "AsyncClient", async_client_factory)


def test_response_size_configuration_is_finite_and_bounded() -> None:
    config = CalClientConfig()
    assert 1 <= config.max_response_bytes <= 16 * 1024 * 1024

    CalClientConfig(max_response_bytes=16 * 1024 * 1024)
    with pytest.raises(ValueError, match="max_response_bytes"):
        CalClientConfig(max_response_bytes=0)
    with pytest.raises(ValueError, match="max_response_bytes"):
        CalClientConfig(max_response_bytes=16 * 1024 * 1024 + 1)


@pytest.mark.parametrize("value", [True, 1.5, "6"])
def test_response_size_configuration_rejects_non_integer_values(value: object) -> None:
    with pytest.raises(ValueError, match="max_response_bytes"):
        CalClientConfig(max_response_bytes=value)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_production_transport_accepts_response_exactly_at_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = CountingStream((b"<ht", b"ml>"))

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "text/html"},
            stream=stream,
            request=request,
        )

    patch_httpx2_transport(monkeypatch, handler)
    config = CalClientConfig(max_response_bytes=6)
    transport = client_module._Httpx2Transport(config)
    try:
        response = await transport(CalRequest(method="GET", path="entry.php"), config)
    finally:
        await transport.aclose()

    assert response.body == b"<html>"
    assert stream.yielded == 2
    assert stream.closed is True


@pytest.mark.anyio
async def test_production_transport_stops_stream_when_response_exceeds_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = CountingStream((b"abc", b"def", b"ghi", b"must-not-be-read"))

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "text/html"},
            stream=stream,
            request=request,
        )

    patch_httpx2_transport(monkeypatch, handler)
    config = CalClientConfig(max_response_bytes=6)
    transport = client_module._Httpx2Transport(config)
    try:
        with pytest.raises(CalResponseTooLargeError) as exc_info:
            await transport(CalRequest(method="GET", path="entry.php"), config)
    finally:
        await transport.aclose()

    assert exc_info.value.max_response_bytes == 6
    assert stream.yielded == 3
    assert stream.closed is True


@pytest.mark.anyio
async def test_oversized_response_is_not_retried_parsed_or_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream_calls = 0
    parser_calls = 0

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal upstream_calls
        upstream_calls += 1
        return httpx2.Response(
            200,
            headers={"content-type": "text/html"},
            stream=CountingStream((b"1234", b"5678")),
            request=request,
        )

    patch_httpx2_transport(monkeypatch, handler)
    client = CalHttpClient(
        config=CalClientConfig(
            max_response_bytes=6,
            max_retries=3,
            retry_backoff_seconds=0,
        )
    )

    def parser(response: CalResponse) -> str:
        nonlocal parser_calls
        parser_calls += 1
        return response.body.decode()

    request = CalRequest(method="GET", path="entry.php")
    try:
        for _ in range(2):
            with pytest.raises(CalResponseTooLargeError):
                await client.fetch(request, parser=parser, cache_namespace="entry")
    finally:
        await client.aclose()

    assert upstream_calls == 2
    assert parser_calls == 0
