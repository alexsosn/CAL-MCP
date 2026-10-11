"""A failed permitted Retry-After retry must not erase its earlier CAL 429 (#293)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalHttpClient,
    CalNetworkError,
    CalRateLimitCooldownError,
    CalRequest,
    CalResponse,
    CalResponseTooLargeError,
    CalUpstreamError,
)
from cal_mcp.errors import classify_public_tool_error


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds
        await asyncio.sleep(0)


def request(word: int) -> CalRequest:
    return CalRequest("GET", "getlex.php", params=(("word", str(word)),))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "failed_retry", ["http503", "redirect302", "timeout", "oserror", "too_large"]
)
async def test_terminal_failure_after_short_hint_429_keeps_protective_cooldown(
    failed_retry: str,
) -> None:
    clock = Clock()
    attempts = 0

    async def transport(req: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del req, config
        attempts += 1
        if attempts == 2:
            if failed_retry == "timeout":
                raise TimeoutError("synthetic timeout")
            if failed_retry == "oserror":
                raise OSError("synthetic network failure")
            if failed_retry == "too_large":
                raise CalResponseTooLargeError("https://cal.huc.edu/getlex.php?word=8", 128)
        status = 429 if attempts == 1 else 200
        if attempts == 2 and failed_retry == "http503":
            status = 503
        if attempts == 2 and failed_retry == "redirect302":
            status = 302
        return CalResponse(
            status_code=status,
            url="https://cal.huc.edu/getlex.php?word=8",
            body=b"<html>synthetic</html>",
            content_type="text/html",
            retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
            retry_after="1" if status == 429 else None,
        )

    client = CalHttpClient(
        config=CalClientConfig(max_retries=1, min_request_interval_seconds=0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )

    if failed_retry in {"http503", "redirect302"}:
        with pytest.raises(CalUpstreamError) as original:
            await client.fetch(request(8), parser=lambda page: page.body, cache_namespace="token")
        assert original.value.status_code == (503 if failed_retry == "http503" else 302)
        classified = classify_public_tool_error("cal_token_analysis", original.value)
        assert classified is not None
        assert classified.to_dict()["error"]["status_code"] == original.value.status_code
    elif failed_retry == "too_large":
        with pytest.raises(CalResponseTooLargeError) as oversized:
            await client.fetch(request(8), parser=lambda page: page.body, cache_namespace="token")
        classified = classify_public_tool_error("cal_token_analysis", oversized.value)
        assert classified is not None
        details = classified.to_dict()["error"]
        assert details["kind"] == "response_too_large"
        assert details["source_url"] == "https://cal.huc.edu/getlex.php?word=8"
        assert details["upstream_reached"] is True
    else:
        with pytest.raises(CalNetworkError):
            await client.fetch(request(8), parser=lambda page: page.body, cache_namespace="token")
    assert attempts == 2

    # The retry did not succeed. Even if CAL's short hint has expired, a
    # different operation must not produce another live CAL transport.
    clock.now += 1.5
    with pytest.raises(CalRateLimitCooldownError) as suppressed:
        await client.fetch(request(9), parser=lambda page: page.body, cache_namespace="token")
    classified = classify_public_tool_error("cal_token_analysis", suppressed.value)
    assert classified is not None
    fields = classified.to_dict()["error"]
    assert fields["kind"] == "upstream_http"
    assert fields["status_code"] == 429
    assert fields["upstream_reached"] is False
    assert fields["source_url"] is None
    assert attempts == 2

    clock.now += 60
    recovered = await client.fetch(
        request(9), parser=lambda page: page.body, cache_namespace="token"
    )
    assert recovered.value == b"<html>synthetic</html>"
    assert attempts == 3
