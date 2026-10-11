"""Deterministic clock-coherence regressions for #311. No CAL I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRateLimitCooldownError,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def request(word: int) -> CalRequest:
    return CalRequest("GET", "getlex.php", (("word", str(word)),))


@pytest.mark.anyio
async def test_injected_clock_controls_completed_cache_ttl_at_exact_boundary() -> None:
    clock = FakeClock()
    starts = 0
    base = datetime(2026, 10, 11, tzinfo=UTC)

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal starts
        del req, config
        starts += 1
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/getlex.php?word=1",
            body=str(starts).encode(),
            content_type="text/html",
            retrieved_at=base + timedelta(minutes=starts),
        )

    client = CalHttpClient(
        config=CalClientConfig(cache_ttl_seconds=2, max_retries=0),
        transport=transport,
        clock=clock,
    )

    first = await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="ttl")
    assert first.value == b"1"
    assert not first.cache_hit
    clock.advance(1.999)
    cached = await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="ttl")
    assert cached.cache_hit
    assert cached.value == b"1"
    assert cached.retrieved_at == first.retrieved_at
    assert cached.cache_age_seconds == pytest.approx(1.999)
    assert starts == 1

    clock.advance(0.001)
    expired = await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="ttl")
    assert not expired.cache_hit
    assert expired.value == b"2"
    assert expired.retrieved_at == base + timedelta(minutes=2)
    assert expired.cache_age_seconds is None
    assert starts == 2


@pytest.mark.anyio
async def test_expired_injected_clock_cache_cannot_bypass_terminal_429_cooldown() -> None:
    clock = FakeClock()
    starts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal starts
        del config
        starts += 1
        is_rate_limited = req.params == (("word", "2"),)
        return CalResponse(
            status_code=429 if is_rate_limited else 200,
            url="https://cal.huc.edu/getlex.php",
            body=b"<html>success</html>",
            content_type="text/html",
            retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        )

    client = CalHttpClient(
        config=CalClientConfig(cache_ttl_seconds=2, max_retries=0),
        transport=transport,
        clock=clock,
    )

    first = await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="ttl")
    assert not first.cache_hit
    with pytest.raises(CalUpstreamError) as upstream:
        await client.fetch(request(2), parser=lambda r: r.body, cache_namespace="ttl")
    assert upstream.value.status_code == 429
    assert starts == 2

    clock.advance(1)
    valid_hit = await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="ttl")
    assert valid_hit.cache_hit
    assert starts == 2

    clock.advance(1)
    with pytest.raises(CalRateLimitCooldownError):
        await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="ttl")
    assert starts == 2
