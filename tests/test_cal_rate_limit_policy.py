"""Offline request-policy regression tests for actual CAL 429 evidence (#262)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx2
import pytest

import cal_mcp.client as client_module
from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)
from cal_mcp.errors import classify_public_tool_error


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.waits: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        assert delay >= 0
        self.waits.append(delay)
        self.now += delay
        await asyncio.sleep(0)


def reply(code: int = 200, *, retry_after: str | None = None) -> CalResponse:
    return CalResponse(
        status_code=code,
        url="https://cal.huc.edu/getlex.php?coord=620430101&word=1",
        body=b"<html><body>fixture</body></html>",
        content_type="text/html",
        retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        retry_after=retry_after,
    )


def request(n: int) -> CalRequest:
    return CalRequest(method="GET", path="getlex.php", params=(("coord", str(n)),))


@pytest.mark.parametrize("invalid", [-1, 6.0, float("nan"), float("inf"), True, "1"])
def test_request_interval_rejects_out_of_policy_values(invalid: object) -> None:
    with pytest.raises(ValueError, match="min_request_interval_seconds"):
        CalClientConfig(min_request_interval_seconds=invalid)  # type: ignore[arg-type]


def test_pacing_config_accepts_offline_override_and_conservative_interval() -> None:
    assert CalClientConfig(min_request_interval_seconds=0).min_request_interval_seconds == 0
    assert CalClientConfig(min_request_interval_seconds=1).min_request_interval_seconds == 1


@pytest.mark.anyio
async def test_sequential_and_cached_requests_pace_only_actual_transport() -> None:
    clock = FakeClock()
    observed: list[float] = []

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        observed.append(clock())
        return reply()

    client = CalHttpClient(
        config=CalClientConfig(min_request_interval_seconds=1.0, max_retries=0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    for n in range(3):
        await client.fetch(request(n), parser=lambda value: value.body, cache_namespace="paced")
    await client.fetch(request(2), parser=lambda value: value.body, cache_namespace="paced")
    assert observed == pytest.approx([100.0, 101.0, 102.0])
    assert clock.waits == pytest.approx([1.0, 1.0])


@pytest.mark.anyio
async def test_concurrent_distinct_calls_reserve_distinct_transport_starts() -> None:
    clock = FakeClock()
    starts: list[float] = []

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        starts.append(clock())
        return reply()

    client = CalHttpClient(
        config=CalClientConfig(min_request_interval_seconds=1.0, max_concurrency=4),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    calls = [
        client.fetch(request(n), parser=lambda x: x.body, cache_namespace="parallel")
        for n in range(4)
    ]
    await asyncio.gather(*calls)
    assert starts == pytest.approx([100.0, 101.0, 102.0, 103.0])


@pytest.mark.anyio
async def test_429_without_hint_is_typed_retryable_and_not_automatically_retried() -> None:
    attempts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del req, config
        attempts += 1
        return reply(429)

    client = CalHttpClient(
        config=CalClientConfig(min_request_interval_seconds=0, max_retries=3),
        transport=transport,
    )
    with pytest.raises(CalUpstreamError) as exc:
        await client.fetch(request(1), parser=lambda x: x.body, cache_namespace="limit")
    public = classify_public_tool_error("cal_token_analysis", exc.value)
    assert public is not None
    assert public.to_dict()["error"]["kind"] == "upstream_http"
    assert public.to_dict()["error"]["status_code"] == 429
    assert public.to_dict()["error"]["retryable"] is True
    assert attempts == 1


@pytest.mark.anyio
async def test_short_retry_after_one_retry_is_paced_and_counted() -> None:
    clock = FakeClock()
    starts: list[float] = []
    counted: list[int] = []

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        starts.append(clock())
        return reply(429, retry_after="1") if len(starts) == 1 else reply()

    client = CalHttpClient(
        config=CalClientConfig(max_retries=3, min_request_interval_seconds=1.0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
        before_transport_attempt=lambda: counted.append(1),
    )
    result = await client.fetch(request(1), parser=lambda x: x.body, cache_namespace="limit")
    assert result.value
    assert starts == pytest.approx([100, 101])
    assert len(counted) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("hint", [None, "", "0", "-1", "3", "99999", "garbage", "1.2"])
async def test_unusable_retry_after_never_triggers_early_retry(hint: str | None) -> None:
    clock = FakeClock()
    attempts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del req, config
        attempts += 1
        return reply(429, retry_after=hint)

    client = CalHttpClient(
        config=CalClientConfig(min_request_interval_seconds=1.0, max_retries=3),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(CalUpstreamError) as exc:
        await client.fetch(request(1), parser=lambda x: x.body, cache_namespace="limit")
    assert exc.value.status_code == 429
    assert attempts == 1
    assert clock.waits == []


@pytest.mark.anyio
async def test_production_client_defaults_paced_and_injected_offline_transport_stays_fast() -> None:
    async def fake(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        return reply()

    production = CalHttpClient()
    try:
        assert production.config.min_request_interval_seconds == 1.0
    finally:
        await production.aclose()

    injected = CalHttpClient(transport=fake)
    assert injected.config.min_request_interval_seconds == 0.0


@pytest.mark.anyio
async def test_production_httpx2_retains_only_429_retry_after_without_reading_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = httpx2.AsyncClient
    received: list[str] = []

    async def handler(req: httpx2.Request) -> httpx2.Response:
        received.append(str(req.url))
        return httpx2.Response(
            429,
            headers={"Retry-After": "2", "Content-Type": "text/plain"},
            content=b"error-body-must-not-be-consumed",
            request=req,
        )

    mock = httpx2.MockTransport(handler)

    def factory(**kwargs: object) -> httpx2.AsyncClient:
        return original(transport=mock, **kwargs)

    monkeypatch.setattr(client_module.httpx2, "AsyncClient", factory)
    config = CalClientConfig()
    transport = client_module._Httpx2Transport(config)
    try:
        result = await transport(request(1), config)
    finally:
        await transport.aclose()

    assert len(received) == 1
    assert result.status_code == 429
    assert result.retry_after == "2"
    assert result.body == b""


@pytest.mark.anyio
async def test_429_retry_does_not_start_after_queued_pacing_slot_exceeds_deadline() -> None:
    """The hint alone fits 15s, but the next CAL slot does not."""
    clock = FakeClock()
    attempts = 0
    counted = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del req, config
        attempts += 1
        if attempts == 1:
            # Model another CAL call reserving a far-later slot in this client.
            client._next_attempt_at = clock() + 30
            return reply(429, retry_after="1")
        return reply()

    def count_attempt() -> None:
        nonlocal counted
        counted += 1

    client = CalHttpClient(
        config=CalClientConfig(
            min_request_interval_seconds=1.0, total_timeout_seconds=15, max_retries=3
        ),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
        before_transport_attempt=count_attempt,
    )
    with pytest.raises(CalUpstreamError) as exc:
        await client.fetch(request(1), parser=lambda value: value.body, cache_namespace="limit")
    assert exc.value.status_code == 429
    assert attempts == 1
    assert counted == 1
    assert clock() < 115
