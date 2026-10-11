"""Regression for cancelling a short Retry-After wait after a real CAL 429 (#291)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalRateLimitCooldownError,
    CalRequest,
    CalResponse,
)
from cal_mcp.errors import classify_public_tool_error


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def request(word: int) -> CalRequest:
    return CalRequest("GET", "getlex.php", params=(("word", str(word)),))


@pytest.mark.anyio
@pytest.mark.parametrize("cancel_during_pace", [False, True])
async def test_cancellation_during_429_retry_wait_keeps_terminal_safety_cooldown(
    cancel_during_pace: bool,
) -> None:
    clock = FakeClock()
    retry_wait_started = asyncio.Event()
    calls: list[int] = []

    async def sleep(delay: float) -> None:
        if cancel_during_pace and delay == 1:
            clock.advance(delay)
            await asyncio.sleep(0)
            return
        assert delay == (4 if cancel_during_pace else 1)
        retry_wait_started.set()
        # Never finish normally: only task cancellation releases this wait.
        await asyncio.Event().wait()

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        calls.append(int(req.params[0][1]))
        if cancel_during_pace and len(calls) == 1:
            # A distinct caller has reserved the slot that follows the hint.
            client._next_attempt_at = clock() + 5
        return CalResponse(
            status_code=429 if len(calls) == 1 else 200,
            url="https://cal.huc.edu/getlex.php?word=8",
            body=b"<html>synthetic</html>",
            content_type="text/html",
            retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
            retry_after="1" if len(calls) == 1 else None,
        )

    client = CalHttpClient(
        config=CalClientConfig(max_retries=1, min_request_interval_seconds=0),
        transport=transport,
        clock=clock,
        sleep=sleep,
    )
    pending = asyncio.create_task(
        client.fetch(request(8), parser=lambda page: page.body, cache_namespace="token")
    )
    await asyncio.wait_for(retry_wait_started.wait(), timeout=5)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    assert calls == [8]
    # CAL already returned a 429. Cancelled work must not lift the protective
    # cooldown as soon as the otherwise-retryable one-second hint expires.
    clock.advance(4.5 if cancel_during_pace else 1.5)
    with pytest.raises(CalRateLimitCooldownError) as suppressed:
        await client.fetch(request(9), parser=lambda page: page.body, cache_namespace="token")
    public = classify_public_tool_error("cal_token_analysis", suppressed.value)
    assert public is not None
    details = public.to_dict()["error"]
    assert details["kind"] == "upstream_http"
    assert details["status_code"] == 429
    assert details["upstream_reached"] is False
    assert details["source_url"] is None
    assert details["retryable"] is True
    assert calls == [8]
    assert suppressed.value.remaining_seconds >= (55 if cancel_during_pace else 58)

    clock.advance(58.5)
    resumed = await client.fetch(request(9), parser=lambda page: page.body, cache_namespace="token")
    assert resumed.value == b"<html>synthetic</html>"
    assert calls == [8, 9]
