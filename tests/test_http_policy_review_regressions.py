from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlsplit

import httpx2
import pytest

import cal_mcp.client as client_module
from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalNetworkError,
    CalRequest,
    CalResponse,
)

Parser = Callable[[CalResponse], str]


class BlockingTransport:
    def __init__(self, outcome: CalResponse | BaseException) -> None:
        self.outcome = outcome
        self.requests: list[CalRequest] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        self.started.set()
        await self.release.wait()
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class CountingTransport:
    def __init__(self, outcome: CalResponse | BaseException) -> None:
        self.outcome = outcome
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def html_response() -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/example.php",
        body=b"<html><body>ok</body></html>",
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )


def parse_text(response: CalResponse) -> str:
    return response.body.decode()


@pytest.mark.anyio
async def test_production_httpx2_boundary_preserves_repeated_fields_and_blocks_redirect_escape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_async_client = httpx2.AsyncClient
    observed: list[tuple[str, str, str, bytes]] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        body = await request.aread()
        observed.append(
            (
                request.method,
                str(request.url),
                request.headers.get("user-agent", ""),
                body,
            )
        )
        if request.url.path == "/redirect.php":
            return httpx2.Response(
                302,
                headers={"location": "https://example.org/escape"},
                request=request,
            )
        return httpx2.Response(
            200,
            headers={"content-type": "text/html; charset=UTF-8"},
            content=b"<html><body>ok</body></html>",
            request=request,
        )

    mock_transport = httpx2.MockTransport(handler)

    def async_client_factory(**kwargs: object) -> httpx2.AsyncClient:
        return real_async_client(transport=mock_transport, **kwargs)

    monkeypatch.setattr(client_module.httpx2, "AsyncClient", async_client_factory)

    config = CalClientConfig()
    transport = client_module._Httpx2Transport(config)
    try:
        post_response = await transport(
            CalRequest(
                method="POST",
                path="submit.php",
                params=(("q", "one"), ("q", "two")),
                data=(("field", "alpha"), ("field", "beta")),
            ),
            config,
        )
        redirect_response = await transport(
            CalRequest(method="GET", path="redirect.php"),
            config,
        )
    finally:
        await transport.aclose()

    assert post_response.status_code == 200
    assert redirect_response.status_code == 302
    assert len(observed) == 2

    method, url, user_agent, body = observed[0]
    assert method == "POST"
    assert parse_qsl(urlsplit(url).query, keep_blank_values=True) == [
        ("q", "one"),
        ("q", "two"),
    ]
    assert parse_qsl(body.decode(), keep_blank_values=True) == [
        ("field", "alpha"),
        ("field", "beta"),
    ]
    assert user_agent == config.user_agent

    assert urlsplit(observed[1][1]).netloc == "cal.huc.edu"
    assert all(urlsplit(item[1]).netloc != "example.org" for item in observed)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "failure",
    [
        httpx2.LocalProtocolError("local protocol error"),
        OSError("local operating-system error"),
    ],
)
async def test_non_retryable_transport_failures_get_exactly_one_attempt(
    failure: BaseException,
) -> None:
    transport = CountingTransport(failure)
    client = CalHttpClient(
        config=CalClientConfig(max_retries=3, retry_backoff_seconds=0),
        transport=transport,
    )

    with pytest.raises(CalNetworkError):
        await client.fetch(
            CalRequest(method="GET", path="entry.php"),
            parser=parse_text,
            cache_namespace="entry",
        )

    assert len(transport.requests) == 1


def test_retry_backoff_configuration_has_conservative_upper_bound() -> None:
    CalClientConfig(retry_backoff_seconds=1.0)

    with pytest.raises(ValueError, match="retry_backoff_seconds"):
        CalClientConfig(retry_backoff_seconds=1.000001)


@pytest.mark.anyio
async def test_simultaneous_identical_requests_are_single_flight() -> None:
    transport = BlockingTransport(html_response())
    client = CalHttpClient(transport=transport)
    request = CalRequest(method="GET", path="entry.php", params=(("lemma", "br N"),))

    first = asyncio.create_task(
        client.fetch(request, parser=parse_text, cache_namespace="entry")
    )
    second = asyncio.create_task(
        client.fetch(request, parser=parse_text, cache_namespace="entry")
    )

    await transport.started.wait()
    await asyncio.sleep(0)
    assert len(transport.requests) == 1

    transport.release.set()
    first_result, second_result = await asyncio.gather(first, second)

    assert len(transport.requests) == 1
    assert first_result.value == second_result.value
