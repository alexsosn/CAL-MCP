"""Offline source-grounded transport admission policy for #297; never queries CAL."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import classify_public_tool_error


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.waits: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)


def request(n: int) -> CalRequest:
    return CalRequest(method="GET", path="getlex.php", params=(("word", str(n)),))


def response(status: int = 200, *, retry_after: str | None = None) -> CalResponse:
    return CalResponse(
        status_code=status,
        url="https://cal.huc.edu/getlex.php?word=0",
        body=b"<html>fixture</html>",
        content_type="text/html",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        retry_after=retry_after,
    )


@pytest.mark.anyio
async def test_eight_rolling_starts_and_honest_ninth_local_rejection_then_expiry() -> None:
    clock = FakeClock()
    starts: list[float] = []
    hooks: list[float] = []

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        starts.append(clock())
        return response()

    client = CalHttpClient(
        config=CalClientConfig(
            max_cal_attempts_per_60s=8,
            min_request_interval_seconds=3.0,
            max_retries=0,
        ),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
        before_transport_attempt=lambda: hooks.append(clock()),
    )
    for n in range(8):
        await client.fetch(request(n), parser=lambda r: r.body, cache_namespace="window")
    assert starts == pytest.approx([100, 103, 106, 109, 112, 115, 118, 121])
    assert hooks == starts

    with pytest.raises(Exception) as exc:
        await client.fetch(request(8), parser=lambda r: r.body, cache_namespace="window")
    assert type(exc.value).__name__ == "CalLocalRequestBudgetError"
    assert len(starts) == len(hooks) == 8
    public = classify_public_tool_error("cal_token_analysis", exc.value)
    assert public is not None
    assert public.to_dict()["error"] == {
        "kind": "local_rate_limit",
        "operation": "cal_token_analysis",
        "upstream_reached": False,
        "retryable": True,
        "message": "CAL-MCP local transport budget exhausted; retry after at least 39 seconds",
        "source_url": None,
        "status_code": None,
    }

    # The oldest start expires at exactly 60 s; boundary is inclusive.
    clock.now = 160.0
    result = await client.fetch(request(8), parser=lambda r: r.body, cache_namespace="window")
    assert not result.cache_hit
    assert starts[-1] == 160.0
    assert len(starts) == len(hooks) == 9


@pytest.mark.anyio
async def test_cached_hit_does_not_consume_rolling_slot() -> None:
    starts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal starts
        del req, config
        starts += 1
        return response()

    client = CalHttpClient(
        config=CalClientConfig(max_cal_attempts_per_60s=1, max_retries=0),
        transport=transport,
    )
    first = await client.fetch(request(0), parser=lambda r: r.body, cache_namespace="cache")
    second = await client.fetch(request(0), parser=lambda r: r.body, cache_namespace="cache")
    assert not first.cache_hit
    assert second.cache_hit
    assert starts == 1
    with pytest.raises(Exception) as exc:
        await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="cache")
    assert type(exc.value).__name__ == "CalLocalRequestBudgetError"
    assert starts == 1


@pytest.mark.anyio
async def test_rolling_budget_serializes_concurrent_zero_interval_attempts() -> None:
    starts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal starts
        del req, config
        starts += 1
        await asyncio.sleep(0)
        return response()

    client = CalHttpClient(
        config=CalClientConfig(
            max_cal_attempts_per_60s=2,
            min_request_interval_seconds=0,
            max_retries=0,
            max_concurrency=4,
        ),
        transport=transport,
    )
    results = await asyncio.gather(
        *(
            client.fetch(request(n), parser=lambda r: r.body, cache_namespace="concurrent")
            for n in range(5)
        ),
        return_exceptions=True,
    )
    assert starts == 2
    assert sum(not isinstance(result, BaseException) for result in results) == 2
    assert [type(result).__name__ for result in results if isinstance(result, BaseException)] == [
        "CalLocalRequestBudgetError"
    ] * 3


@pytest.mark.anyio
async def test_failed_before_attempt_hook_does_not_consume_rolling_slot() -> None:
    transport_starts = 0
    hook_invocations = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal transport_starts
        del req, config
        transport_starts += 1
        return response()

    def before_attempt() -> None:
        nonlocal hook_invocations
        hook_invocations += 1
        if hook_invocations == 1:
            raise RuntimeError("synthetic denied smoke attempt")

    client = CalHttpClient(
        config=CalClientConfig(max_cal_attempts_per_60s=1, max_retries=0),
        transport=transport,
        before_transport_attempt=before_attempt,
    )
    with pytest.raises(RuntimeError, match="synthetic denied smoke attempt"):
        await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="hook")
    success = await client.fetch(request(2), parser=lambda r: r.body, cache_namespace="hook")
    assert success.value
    with pytest.raises(Exception) as exc:
        await client.fetch(request(3), parser=lambda r: r.body, cache_namespace="hook")
    assert type(exc.value).__name__ == "CalLocalRequestBudgetError"
    assert hook_invocations == 2
    assert transport_starts == 1


@pytest.mark.anyio
async def test_retries_count_as_separate_cal_transport_starts() -> None:
    statuses = [503, 200]
    starts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal starts
        del req, config
        starts += 1
        return response(statuses.pop(0))

    client = CalHttpClient(
        config=CalClientConfig(
            max_cal_attempts_per_60s=1,
            min_request_interval_seconds=0,
            retry_backoff_seconds=0,
            max_retries=1,
        ),
        transport=transport,
    )
    with pytest.raises(Exception) as exc:
        await client.fetch(request(0), parser=lambda r: r.body, cache_namespace="retry")
    assert type(exc.value).__name__ == "CalLocalRequestBudgetError"
    assert starts == 1
    assert statuses == [200]
    public = classify_public_tool_error("cal_token_analysis", exc.value)
    assert public is not None
    assert public.to_dict()["error"]["upstream_reached"] is True
    assert public.to_dict()["error"]["status_code"] is None


@pytest.mark.anyio
async def test_local_budget_blocked_429_retry_reports_original_429_and_real_cooldown() -> None:
    clock = FakeClock()
    starts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal starts
        del req, config
        starts += 1
        return response(429, retry_after="1")

    client = CalHttpClient(
        config=CalClientConfig(
            max_cal_attempts_per_60s=1,
            max_retries=1,
            min_request_interval_seconds=0,
        ),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(Exception) as exc:
        await client.fetch(request(1), parser=lambda r: r.body, cache_namespace="429-window")
    assert type(exc.value).__name__ == "CalUpstreamError"
    assert starts == 1
    public = classify_public_tool_error("cal_token_analysis", exc.value)
    assert public is not None
    envelope = public.to_dict()["error"]
    assert envelope["upstream_reached"] is True
    assert envelope["kind"] == "upstream_http"
    assert envelope["status_code"] == 429
    assert "local cooldown at least 60 seconds" in str(envelope["message"])
    with pytest.raises(Exception) as follow_up:
        await client.fetch(request(2), parser=lambda r: r.body, cache_namespace="429-window")
    assert type(follow_up.value).__name__ == "CalRateLimitCooldownError"
    assert starts == 1


@pytest.mark.anyio
async def test_real_and_smoke_paths_default_to_cap_but_injected_fake_stays_explicit() -> None:
    import cal_mcp.server as server

    real = CalHttpClient()
    try:
        assert real.config.max_cal_attempts_per_60s == 8
    finally:
        await real.aclose()

    async def fake(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del req, config
        return response()

    assert CalHttpClient(transport=fake).config.max_cal_attempts_per_60s is None
    assert CalClientConfig().max_cal_attempts_per_60s is None

    from unittest.mock import patch

    with patch.dict("os.environ", {"CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS": "25"}):
        async with server.app_lifespan(server.mcp) as context:
            assert context.client.config.max_cal_attempts_per_60s == 8


@pytest.mark.parametrize("value", [0, -1, 26, True, 2.5, "8"])
def test_window_config_rejects_unsafe_budgets(value: object) -> None:
    with pytest.raises(ValueError, match="max_cal_attempts_per_60s"):
        CalClientConfig(max_cal_attempts_per_60s=value)  # type: ignore[arg-type]
