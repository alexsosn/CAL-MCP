from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.smoke_budget import SmokeAttemptBudget, SmokeBudgetExceeded
from cal_mcp.server import app_lifespan, mcp


def _response() -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/example.php",
        body=b"<html><body>ok</body></html>",
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_smoke_budget_guards_real_attempts_and_cache_hits_are_free() -> None:
    sent: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        sent.append(request)
        return _response()

    budget = SmokeAttemptBudget(max_attempts=2)
    client = CalHttpClient(
        transport=transport, before_transport_attempt=budget.before_attempt
    )
    try:
        one = CalRequest("GET", "entry.php", params=(("lemma", "br N"),))
        two = CalRequest("GET", "entry.php", params=(("lemma", "ktb V"),))
        three = CalRequest("GET", "entry.php", params=(("lemma", ")mr V"),))
        await client.fetch(one, parser=lambda x: x.body, cache_namespace="entry")
        cached = await client.fetch(one, parser=lambda x: x.body, cache_namespace="entry")
        assert cached.cache_hit
        await client.fetch(two, parser=lambda x: x.body, cache_namespace="entry")
        with pytest.raises(SmokeBudgetExceeded):
            await client.fetch(three, parser=lambda x: x.body, cache_namespace="entry")
        assert budget.attempts == 2
        assert len(sent) == 2
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_smoke_budget_counts_every_retry_before_transport() -> None:
    attempts = 0

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del request, config
        attempts += 1
        if attempts == 1:
            raise TimeoutError("synthetic network timeout")
        return _response()

    budget = SmokeAttemptBudget(max_attempts=2)
    client = CalHttpClient(
        config=CalClientConfig(max_retries=1, retry_backoff_seconds=0),
        transport=transport,
        before_transport_attempt=budget.before_attempt,
    )
    try:
        result = await client.fetch(
            CalRequest("GET", "entry.php"), parser=lambda x: x.body, cache_namespace="entry"
        )
        assert result.value
        assert attempts == budget.attempts == 2
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_regular_client_has_no_implicit_smoke_budget() -> None:
    attempts = 0

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        nonlocal attempts
        del request, config
        attempts += 1
        return _response()

    client = CalHttpClient(transport=transport)
    try:
        for i in range(26):
            await client.fetch(
                CalRequest("GET", "entry.php", params=(("index", str(i)),)),
                parser=lambda x: x.body,
                cache_namespace="entry",
            )
        assert attempts == 26
    finally:
        await client.aclose()


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "25"])
def test_smoke_budget_rejects_invalid_limits(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        SmokeAttemptBudget(max_attempts=value)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_smoke_stdio_lifespan_caps_attempts_without_default_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS", "25")
    async with app_lifespan(mcp) as context:
        client = context.client
        assert client.config.max_concurrency == 1
        assert client.config.max_retries == 0
        assert client.config.cache_enabled
        guard = client._before_transport_attempt
        assert guard is not None
        for _ in range(25):
            guard()
        with pytest.raises(SmokeBudgetExceeded):
            guard()


@pytest.mark.anyio
async def test_normal_stdio_lifespan_never_inherits_smoke_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS", raising=False)
    async with app_lifespan(mcp) as context:
        assert context.client._before_transport_attempt is None


@pytest.mark.anyio
async def test_smoke_stdio_lifespan_rejects_attempts_cap_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS", "26")
    with pytest.raises(ValueError, match="reviewed 25-attempt cap"):
        async with app_lifespan(mcp):
            pytest.fail("invalid smoke cap must not start a CAL client")
