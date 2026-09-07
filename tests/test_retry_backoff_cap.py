from __future__ import annotations

from datetime import UTC, datetime

import pytest

import cal_mcp.client as client_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse


def html_response(*, status_code: int = 200) -> CalResponse:
    return CalResponse(
        status_code=status_code,
        url="https://cal.huc.edu/example.php",
        body=b"<html><body>ok</body></html>",
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 7, tzinfo=UTC),
    )


class ScriptedTransport:
    def __init__(self, outcomes: list[CalResponse | BaseException]) -> None:
        self.outcomes = outcomes
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        outcome = self.outcomes[len(self.requests) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.mark.anyio
@pytest.mark.parametrize(
    "outcomes",
    [
        [
            html_response(status_code=503),
            html_response(status_code=503),
            html_response(status_code=503),
            html_response(),
        ],
        [
            TimeoutError("first timeout"),
            TimeoutError("second timeout"),
            TimeoutError("third timeout"),
            html_response(),
        ],
    ],
    ids=("transient-status", "transport-timeout"),
)
async def test_retry_backoff_is_exponential_but_capped(
    monkeypatch: pytest.MonkeyPatch,
    outcomes: list[CalResponse | BaseException],
) -> None:
    scheduled_sleeps: list[float] = []

    async def record_sleep(delay: float) -> None:
        scheduled_sleeps.append(delay)

    monkeypatch.setattr(client_module.asyncio, "sleep", record_sleep)
    transport = ScriptedTransport(outcomes)
    client = CalHttpClient(
        config=CalClientConfig(max_retries=3, retry_backoff_seconds=0.4),
        transport=transport,
    )

    result = await client.fetch(
        CalRequest(method="GET", path="example.php"),
        parser=lambda response: response.body.decode(),
        cache_namespace="backoff-cap",
    )

    assert result.value.endswith("</html>")
    assert len(transport.requests) == 4
    assert scheduled_sleeps == pytest.approx([0.4, 0.8, 1.0])
