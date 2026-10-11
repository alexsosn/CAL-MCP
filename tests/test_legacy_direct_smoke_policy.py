"""Offline source-grounded legacy direct smoke safety checks (#313)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalLocalRequestBudgetError,
    CalRateLimitCooldownError,
    CalRequest,
    CalRequestValidationError,
    CalResponse,
)
from cal_mcp.live_smoke import (
    BudgetCalHttpClient,
    LiveSmokeBudgetExceeded,
    LiveSmokeFailure,
    SmokeCase,
    classify_smoke_exception,
    run_live_smoke,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        assert seconds >= 0
        self.now += seconds
        await asyncio.sleep(0)

    def advance(self, seconds: float) -> None:
        self.now += seconds


def request(n: int) -> CalRequest:
    return CalRequest("GET", "getlex.php", (("word", str(n)),))


def reply(status_code: int = 200) -> CalResponse:
    return CalResponse(
        status_code=status_code,
        url="https://cal.huc.edu/getlex.php?word=1",
        body=b"<html><body>fixture</body></html>",
        content_type="text/html",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_direct_live_smoke_paces_and_rejects_ninth_start_inside_rolling_window() -> None:
    clock = FakeClock()
    starts: list[float] = []

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        starts.append(clock())
        return reply()

    client = BudgetCalHttpClient(transport=transport, clock=clock, sleep=clock.sleep)
    assert client.config.min_request_interval_seconds == 3.0
    assert client.config.max_cal_attempts_per_60s == 8
    assert client.config.max_retries == 0
    assert client.config.max_concurrency == 1
    for n in range(8):
        await client.fetch(
            request(n), parser=lambda response: response.body, cache_namespace="probe"
        )
    assert starts == pytest.approx([100 + 3 * n for n in range(8)])
    assert client.request_count == 8

    with pytest.raises(CalLocalRequestBudgetError):
        await client.fetch(
            request(8), parser=lambda response: response.body, cache_namespace="probe"
        )
    assert client.request_count == 8
    assert len(starts) == 8

    clock.advance(39)
    await client.fetch(request(8), parser=lambda response: response.body, cache_namespace="probe")
    assert starts[-1] == 160.0
    assert client.request_count == 9

    clock.advance(60)
    with pytest.raises(LiveSmokeBudgetExceeded):
        await client.fetch(
            request(9), parser=lambda response: response.body, cache_namespace="probe"
        )
    assert client.request_count == 9
    assert len(starts) == 9


@pytest.mark.anyio
async def test_rejected_local_input_is_not_misreported_as_cal_transport() -> None:
    starts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal starts
        del req, config
        starts += 1
        return reply()

    client = BudgetCalHttpClient(transport=transport)
    with pytest.raises(CalRequestValidationError):
        await client.fetch(
            CalRequest("GET", "https://other.example/bad"),
            parser=lambda response: response.body,
            cache_namespace="probe",
        )
    assert client.request_count == 0
    assert starts == 0


def test_local_backpressure_is_not_mislabelled_as_harness_failure() -> None:
    assert classify_smoke_exception(CalLocalRequestBudgetError(12)) == "upstream"
    assert classify_smoke_exception(CalRateLimitCooldownError(60)) == "upstream"


@pytest.mark.anyio
async def test_direct_smoke_true_429_stops_before_following_cases() -> None:
    calls = 0
    visited: list[str] = []

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal calls
        del req, config
        calls += 1
        return reply(429)

    client = BudgetCalHttpClient(transport=transport)

    async def first(smoke_client: BudgetCalHttpClient) -> None:
        visited.append("first")
        await smoke_client.fetch(
            request(1), parser=lambda response: response.body, cache_namespace="probe"
        )

    async def second(smoke_client: BudgetCalHttpClient) -> None:
        visited.append("second")
        await smoke_client.fetch(
            request(2), parser=lambda response: response.body, cache_namespace="probe"
        )

    with pytest.raises(LiveSmokeFailure) as exc:
        await run_live_smoke(
            client=client,
            cases=(SmokeCase("first", first), SmokeCase("second", second)),
        )
    assert exc.value.category == "upstream"
    assert exc.value.request_count == 1
    assert visited == ["first"]
    assert calls == 1
