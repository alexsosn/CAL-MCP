"""Issue #262: 429 stops new CAL I/O across distinct MCP operations."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalClientError,
    CalHttpClient,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)
from cal_mcp.errors import classify_public_tool_error


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.advance(seconds)
        await asyncio.sleep(0)


def response(status_code: int, retry_after: str | None = None) -> CalResponse:
    return CalResponse(
        status_code=status_code,
        url="https://cal.huc.edu/getlex.php?coord=620430101&word=8",
        body=b"<html><body>synthetic</body></html>",
        content_type="text/html",
        retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        retry_after=retry_after,
    )


def request(index: int) -> CalRequest:
    return CalRequest(method="GET", path="getlex.php", params=(("word", str(index)),))


@pytest.mark.anyio
async def test_one_429_blocks_a_different_operation_without_another_CAL_transport() -> None:
    clock = Clock()
    sent: list[int] = []

    async def transport(req: CalRequest, cfg: CalClientConfig) -> CalResponse:
        del cfg
        sent.append(int(req.params[0][1]))
        return response(429) if len(sent) == 1 else response(200)

    client = CalHttpClient(
        config=CalClientConfig(max_retries=0, min_request_interval_seconds=0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(CalUpstreamError) as original:
        await client.fetch(request(8), parser=lambda x: x.body, cache_namespace="lexicon")
    assert original.value.status_code == 429
    assert sent == [8]

    with pytest.raises(CalClientError) as suppressed:
        await client.fetch(request(9), parser=lambda x: x.body, cache_namespace="lexicon")
    public = classify_public_tool_error("cal_token_analysis", suppressed.value)
    assert public is not None
    envelope = public.to_dict()["error"]
    assert envelope["kind"] == "upstream_http"
    assert envelope["status_code"] == 429
    assert envelope["retryable"] is True
    assert envelope["upstream_reached"] is False
    assert envelope["source_url"] is None
    assert "cooldown" in envelope["message"].lower()
    assert sent == [8]
    assert clock.sleeps == []

    clock.advance(60)
    resumed = await client.fetch(request(9), parser=lambda x: x.body, cache_namespace="lexicon")
    assert resumed.value
    assert sent == [8, 9]


@pytest.mark.anyio
async def test_429_cooldown_does_not_suppress_previous_successful_cached_data() -> None:
    clock = Clock()
    sent: list[int] = []

    async def transport(req: CalRequest, cfg: CalClientConfig) -> CalResponse:
        del cfg
        word = int(req.params[0][1])
        sent.append(word)
        return response(429) if word == 8 else response(200)

    client = CalHttpClient(
        config=CalClientConfig(max_retries=0, min_request_interval_seconds=0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    initial = await client.fetch(request(2), parser=lambda x: x.body, cache_namespace="lexicon")
    with pytest.raises(CalUpstreamError):
        await client.fetch(request(8), parser=lambda x: x.body, cache_namespace="lexicon")

    cached = await client.fetch(request(2), parser=lambda x: x.body, cache_namespace="lexicon")
    assert cached.cache_hit is True
    assert cached.value == initial.value
    assert sent == [2, 8]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("header", "blocked_until"),
    [
        (None, 60),
        ("garbage", 60),
        ("90", 90),
        ("0", 60),
    ],
)
async def test_429_long_hint_enforces_local_wait_without_busy_retry(
    header: str | None, blocked_until: int
) -> None:
    clock = Clock()
    attempts = 0

    async def transport(req: CalRequest, cfg: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del req, cfg
        attempts += 1
        return response(429, retry_after=header) if attempts == 1 else response(200)

    client = CalHttpClient(
        config=CalClientConfig(max_retries=3, min_request_interval_seconds=0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(CalUpstreamError):
        await client.fetch(request(8), parser=lambda x: x.body, cache_namespace="lexicon")
    clock.advance(blocked_until - 1)
    with pytest.raises(CalClientError):
        await client.fetch(request(9), parser=lambda x: x.body, cache_namespace="lexicon")
    assert attempts == 1
    clock.advance(1)
    await client.fetch(request(9), parser=lambda x: x.body, cache_namespace="lexicon")
    assert attempts == 2


@pytest.mark.anyio
async def test_successful_short_hint_retry_does_not_leave_terminal_cooldown() -> None:
    clock = Clock()
    attempts = 0

    async def transport(req: CalRequest, cfg: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del req, cfg
        attempts += 1
        return response(429, retry_after="1") if attempts == 1 else response(200)

    client = CalHttpClient(
        config=CalClientConfig(max_retries=1, min_request_interval_seconds=0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    await client.fetch(request(8), parser=lambda x: x.body, cache_namespace="lexicon")
    await client.fetch(request(9), parser=lambda x: x.body, cache_namespace="lexicon")
    assert attempts == 3
    assert clock.sleeps == [1]
