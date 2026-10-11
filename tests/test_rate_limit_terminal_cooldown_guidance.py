"""First CAL HTTP 429 must disclose the locally enforced cooldown (#289)."""

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
    CalUpstreamError,
)
from cal_mcp.errors import classify_public_tool_error

URL = "https://cal.huc.edu/getlex.php?coord=620430101&word=8"


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds
        await asyncio.sleep(0)


def response(hint: str | None) -> CalResponse:
    return CalResponse(
        status_code=429,
        url=URL,
        body=b"",
        content_type="text/html",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        retry_after=hint,
    )


def req() -> CalRequest:
    return CalRequest(method="GET", path="getlex.php", params=(("word", "8"),))


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("hint", "minimum", "upstream_hint"),
    [
        (None, 60, None),
        ("1", 60, 1),
        ("90", 90, 90),
        ("garbage", 60, None),
    ],
)
async def test_terminal_429_discloses_real_local_cooldown_before_client_retries(
    hint: str | None, minimum: int, upstream_hint: int | None
) -> None:
    clock = Clock()
    attempts = 0

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del request, config
        attempts += 1
        return response(hint)

    client = CalHttpClient(
        config=CalClientConfig(min_request_interval_seconds=0, max_retries=0),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(CalUpstreamError) as exc:
        await client.fetch(req(), parser=lambda page: page.body, cache_namespace="test")

    public = classify_public_tool_error("cal_token_analysis", exc.value)
    assert public is not None
    error = public.to_dict()["error"]
    assert error["kind"] == "upstream_http"
    assert error["status_code"] == 429
    assert error["retryable"] is True
    assert error["upstream_reached"] is True
    assert error["source_url"] == URL
    assert f"local cooldown at least {minimum} seconds" in error["message"]
    if upstream_hint is not None:
        assert f"CAL Retry-After {upstream_hint} seconds" in error["message"]
    else:
        assert "Retry-After" not in error["message"]
    assert attempts == 1
    with pytest.raises(CalRateLimitCooldownError):
        await client.fetch(
            CalRequest(method="GET", path="getlex.php", params=(("word", "9"),)),
            parser=lambda page: page.body,
            cache_namespace="test",
        )
    assert attempts == 1


def test_raw_upstream_error_must_not_claim_a_local_cooldown() -> None:
    raw = CalUpstreamError(429, URL, retry_after_seconds=1)
    public = classify_public_tool_error("cal_token_analysis", raw)
    assert public is not None
    message = public.to_dict()["error"]["message"]
    assert "CAL Retry-After 1 seconds" in message
    assert "local cooldown" not in message


@pytest.mark.anyio
async def test_queued_429_retry_deadline_reports_terminal_cooldown_without_new_io() -> None:
    clock = Clock()
    attempts = 0

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del request, config
        attempts += 1
        # Simulate another caller occupying the subsequent pacing slot.
        client._next_attempt_at = clock() + 30
        return response("1")

    client = CalHttpClient(
        config=CalClientConfig(min_request_interval_seconds=1, max_retries=1),
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(CalUpstreamError) as exc:
        await client.fetch(req(), parser=lambda page: page.body, cache_namespace="test")
    public = classify_public_tool_error("cal_token_analysis", exc.value)
    assert public is not None
    message = public.to_dict()["error"]["message"]
    assert "CAL Retry-After 1 seconds" in message
    assert "local cooldown at least 60 seconds" in message
    assert attempts == 1
