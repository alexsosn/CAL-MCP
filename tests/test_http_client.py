from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from cal_mcp.client import (
    CalClientConfig,
    CalContentError,
    CalHttpClient,
    CalNetworkError,
    CalRequest,
    CalRequestValidationError,
    CalResponse,
    CalUpstreamError,
)

Parser = Callable[[CalResponse], str]


class ScriptedTransport:
    def __init__(self, outcomes: list[CalResponse | BaseException]) -> None:
        self.outcomes = outcomes
        self.requests: list[CalRequest] = []
        self.active = 0
        self.max_active = 0
        self.block: asyncio.Event | None = None

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.block is not None:
                await self.block.wait()
            outcome = self.outcomes[min(len(self.requests) - 1, len(self.outcomes) - 1)]
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome
        finally:
            self.active -= 1


def html_response(
    body: str = "<html><body>ok</body></html>",
    *,
    status_code: int = 200,
    url: str = "https://cal.huc.edu/example.php?q=x",
    retrieved_at: datetime | None = None,
    content_type: str = "text/html; charset=UTF-8",
) -> CalResponse:
    return CalResponse(
        status_code=status_code,
        url=url,
        body=body.encode(),
        content_type=content_type,
        retrieved_at=retrieved_at or datetime(2026, 9, 4, tzinfo=UTC),
    )


def parse_text(response: CalResponse) -> str:
    return response.body.decode()


@pytest.mark.anyio
async def test_invalid_request_is_rejected_before_transport() -> None:
    transport = ScriptedTransport([html_response()])
    client = CalHttpClient(transport=transport)

    with pytest.raises(CalRequestValidationError):
        await client.fetch(
            CalRequest(method="GET", path="https://example.org/not-cal"),
            parser=parse_text,
            cache_namespace="test",
        )

    assert transport.requests == []


@pytest.mark.anyio
async def test_identical_request_reuses_parsed_cache_and_preserves_retrieved_at() -> None:
    retrieved_at = datetime(2026, 9, 4, 0, 1, tzinfo=UTC)
    transport = ScriptedTransport([html_response(retrieved_at=retrieved_at)])
    client = CalHttpClient(transport=transport)
    request = CalRequest(method="GET", path="entry.php", params=(("lemma", "br N"),))

    first = await client.fetch(request, parser=parse_text, cache_namespace="entry")
    second = await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert len(transport.requests) == 1
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.retrieved_at == retrieved_at
    assert second.value == first.value


@pytest.mark.anyio
async def test_cache_key_separates_request_parameters_and_parser_namespace() -> None:
    transport = ScriptedTransport([html_response()])
    client = CalHttpClient(transport=transport)

    await client.fetch(
        CalRequest(method="GET", path="entry.php", params=(("lemma", "br N"),)),
        parser=parse_text,
        cache_namespace="entry",
    )
    await client.fetch(
        CalRequest(method="GET", path="entry.php", params=(("lemma", "nmy X"),)),
        parser=parse_text,
        cache_namespace="entry",
    )
    await client.fetch(
        CalRequest(method="GET", path="entry.php", params=(("lemma", "br N"),)),
        parser=parse_text,
        cache_namespace="different-parser",
    )

    assert len(transport.requests) == 3


@pytest.mark.anyio
async def test_cache_can_be_disabled() -> None:
    transport = ScriptedTransport([html_response()])
    config = CalClientConfig(cache_enabled=False)
    client = CalHttpClient(config=config, transport=transport)
    request = CalRequest(method="GET", path="entry.php")

    await client.fetch(request, parser=parse_text, cache_namespace="entry")
    await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_parser_failure_is_never_cached() -> None:
    transport = ScriptedTransport([html_response()])
    client = CalHttpClient(transport=transport)
    request = CalRequest(method="GET", path="entry.php")
    calls = 0

    def failing_parser(response: CalResponse) -> str:
        nonlocal calls
        del response
        calls += 1
        raise ValueError("parser drift")

    for _ in range(2):
        with pytest.raises(ValueError, match="parser drift"):
            await client.fetch(request, parser=failing_parser, cache_namespace="entry")

    assert calls == 2
    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_network_failure_is_bounded_and_not_cached() -> None:
    transport = ScriptedTransport([TimeoutError("timeout")])
    config = CalClientConfig(max_retries=1, retry_backoff_seconds=0)
    client = CalHttpClient(config=config, transport=transport)
    request = CalRequest(method="GET", path="entry.php")

    for _ in range(2):
        with pytest.raises(CalNetworkError):
            await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert len(transport.requests) == 4


@pytest.mark.anyio
async def test_semantic_4xx_is_not_retried() -> None:
    transport = ScriptedTransport([html_response(status_code=404)])
    config = CalClientConfig(max_retries=3, retry_backoff_seconds=0)
    client = CalHttpClient(config=config, transport=transport)

    with pytest.raises(CalUpstreamError) as exc_info:
        await client.fetch(
            CalRequest(method="GET", path="entry.php"),
            parser=parse_text,
            cache_namespace="entry",
        )

    assert exc_info.value.status_code == 404
    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_transient_503_retries_with_finite_budget() -> None:
    transport = ScriptedTransport([html_response(status_code=503), html_response()])
    config = CalClientConfig(max_retries=2, retry_backoff_seconds=0)
    client = CalHttpClient(config=config, transport=transport)

    result = await client.fetch(
        CalRequest(method="GET", path="entry.php"),
        parser=parse_text,
        cache_namespace="entry",
    )

    assert result.value.endswith("</html>")
    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_non_html_response_is_distinct_and_not_cached() -> None:
    transport = ScriptedTransport(
        [html_response(body="not html", content_type="application/json")]
    )
    client = CalHttpClient(transport=transport)
    request = CalRequest(method="GET", path="entry.php")

    for _ in range(2):
        with pytest.raises(CalContentError):
            await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_probable_maintenance_page_is_distinct_and_not_cached() -> None:
    transport = ScriptedTransport(
        [html_response("<html><title>Maintenance</title><body>Please try later</body></html>")]
    )
    client = CalHttpClient(transport=transport)
    request = CalRequest(method="GET", path="entry.php")

    for _ in range(2):
        with pytest.raises(CalContentError, match="maintenance"):
            await client.fetch(request, parser=parse_text, cache_namespace="entry")

    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_concurrency_is_bounded() -> None:
    transport = ScriptedTransport([html_response()])
    transport.block = asyncio.Event()
    client = CalHttpClient(config=CalClientConfig(max_concurrency=2), transport=transport)

    async def fetch(index: int) -> None:
        await client.fetch(
            CalRequest(method="GET", path="entry.php", params=(("n", str(index)),)),
            parser=parse_text,
            cache_namespace="entry",
        )

    tasks = [asyncio.create_task(fetch(index)) for index in range(5)]
    for _ in range(100):
        if transport.max_active == 2:
            break
        await asyncio.sleep(0)

    assert transport.max_active == 2
    transport.block.set()
    await asyncio.gather(*tasks)
    assert transport.max_active == 2


@pytest.mark.anyio
async def test_total_timeout_is_finite() -> None:
    gate = asyncio.Event()

    async def hanging_transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        await gate.wait()
        return html_response()

    client = CalHttpClient(
        config=CalClientConfig(total_timeout_seconds=0.01, max_retries=0),
        transport=hanging_transport,
    )

    with pytest.raises(CalNetworkError, match="timeout"):
        await client.fetch(
            CalRequest(method="GET", path="entry.php"),
            parser=parse_text,
            cache_namespace="entry",
        )


def test_configuration_defaults_are_finite_and_conservative() -> None:
    config = CalClientConfig()

    assert 0 < config.connect_timeout_seconds <= config.total_timeout_seconds
    assert 0 < config.read_timeout_seconds <= config.total_timeout_seconds
    assert 1 <= config.max_concurrency <= 4
    assert 0 <= config.max_retries <= 3
    assert config.cache_enabled is True
    assert 1 <= config.cache_max_entries <= 512
    assert 1 <= config.cache_ttl_seconds <= 3600
    assert "CAL-MCP" in config.user_agent


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("connect_timeout_seconds", 0),
        ("read_timeout_seconds", 0),
        ("total_timeout_seconds", 0),
        ("max_concurrency", 0),
        ("max_retries", -1),
        ("cache_max_entries", -1),
        ("cache_ttl_seconds", 0),
    ],
)
def test_invalid_configuration_is_rejected(field: str, value: int) -> None:
    kwargs = {field: value}
    with pytest.raises(ValueError):
        CalClientConfig(**kwargs)
