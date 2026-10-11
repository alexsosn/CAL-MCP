"""Issue #299: offline smoke-scheduling contracts; zero CAL network traffic."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.errors import PublicErrorKind, PublicToolError
from cal_mcp.stdio_live_smoke import SmokeCase, _run_live, evaluate_smoke_cases


@dataclass
class Clock:
    now: float = 100.0
    waits: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        assert 0 < delay <= 60
        self.waits.append(delay)
        self.now += delay
        await asyncio.sleep(0)


def tool(name: str) -> Tool:
    return Tool(
        name=name,
        description="offline only",
        input_schema={"type": "object"},
        output_schema={
            "type": "object",
            "properties": {"status": {"type": "string"}, "error": {"type": "object"}},
            "anyOf": [{"required": ["status"]}, {"required": ["error"]}],
        },
    )


def result(payload: dict[str, object], *, error: bool = False) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="synthetic")],
        structured_content=payload,
        is_error=error,
    )


@dataclass
class FakeClient:
    clock: Clock
    outcomes: list[CallToolResult]
    available: tuple[str, ...] = ("cal_convert_to_code", "cal_gloss_search")
    calls: list[tuple[str, float]] = field(default_factory=list)

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(tools=[tool(name) for name in self.available])

    async def call_tool(self, name: str, arguments: dict[str, object]) -> CallToolResult:
        del arguments
        self.calls.append((name, self.clock.now))
        return self.outcomes.pop(0)


def smoke_case(name: str, *, local: bool = False) -> SmokeCase:
    return SmokeCase(
        name,
        "cal_convert_to_code" if local else "cal_gloss_search",
        {"query": "fixed"},
        needs_provenance=False,
    )


@pytest.mark.anyio
async def test_live_case_spacing_only_follows_a_called_cal_tool() -> None:
    clock = Clock()
    client = FakeClient(clock, [result({"status": "ok"}) for _ in range(5)])
    cases = (
        smoke_case("local-first", local=True),
        smoke_case("cal-first"),
        smoke_case("cal-second"),
        smoke_case("local-middle", local=True),
        smoke_case("cal-third"),
    )
    outcomes = await evaluate_smoke_cases(
        client, cases, min_cal_case_spacing_seconds=60.0, clock=clock, sleep=clock.sleep
    )
    assert [item.category for item in outcomes] == ["ok"] * 5
    assert client.calls == [
        ("cal_convert_to_code", 100),
        ("cal_gloss_search", 100),
        ("cal_gloss_search", 160),
        ("cal_convert_to_code", 160),
        ("cal_gloss_search", 220),
    ]
    assert clock.waits == [60.0, 60.0]


@pytest.mark.anyio
async def test_failed_and_missing_cases_never_reset_live_cal_spacing() -> None:
    clock = Clock()
    client = FakeClient(
        clock,
        [result({"status": "not_found"}), result({"status": "ok"})],
    )
    cases = (
        smoke_case("failed"),
        SmokeCase(
            "skipped",
            "cal_gloss_search",
            {},
            from_case="failed",
            needs_provenance=False,
        ),
        SmokeCase("unknown", "cal_missing_tool", {}),
        smoke_case("valid"),
    )
    outcomes = await evaluate_smoke_cases(
        client, cases, min_cal_case_spacing_seconds=60.0, clock=clock, sleep=clock.sleep
    )
    assert [o.category for o in outcomes] == [
        "ok",
        "skipped_dependency",
        "harness",
        "ok",
    ]
    assert client.calls == [("cal_gloss_search", 100), ("cal_gloss_search", 160)]
    assert clock.waits == [60]


@pytest.mark.anyio
async def test_smoke_case_wait_is_cancellable_and_does_not_issue_next_tool() -> None:
    clock = Clock()
    client = FakeClient(clock, [result({"status": "ok"}) for _ in range(2)])

    async def cancelled_sleep(delay: float) -> None:
        assert delay == 60.0
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await evaluate_smoke_cases(
            client,
            (smoke_case("first"), smoke_case("second")),
            min_cal_case_spacing_seconds=60,
            clock=clock,
            sleep=cancelled_sleep,
        )
    assert client.calls == [("cal_gloss_search", 100)]


@pytest.mark.anyio
async def test_local_rate_limit_is_typed_unavailable_and_stops_without_retries() -> None:
    clock = Clock()
    locally_rejected = PublicToolError(
        kind=PublicErrorKind.LOCAL_RATE_LIMIT,
        operation="cal_gloss_search",
        upstream_reached=False,
        retryable=True,
        message="CAL-MCP local transport budget exhausted",
        source_url=None,
        status_code=None,
    ).to_dict()
    client = FakeClient(
        clock,
        [result(locally_rejected, error=True), result({"status": "ok"})],
        available=("cal_gloss_search",),
    )
    outcomes = await evaluate_smoke_cases(
        client,
        (smoke_case("local-throttle"), smoke_case("must-not-call")),
        min_cal_case_spacing_seconds=60,
        clock=clock,
        sleep=clock.sleep,
    )
    assert [(o.case, o.category) for o in outcomes] == [
        ("local-throttle", "unavailable")
    ]
    assert client.calls == [("cal_gloss_search", 100)]
    assert clock.waits == []
    assert "CAL-MCP local transport budget exhausted" not in outcomes[0].message


@pytest.mark.anyio
async def test_live_installed_runner_enables_fixed_spacing_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cal_mcp.stdio_live_smoke as smoke

    options: list[float] = []

    class OfflineStdioClient:
        def __init__(self, params: object) -> None:
            self.params = params

        async def __aenter__(self) -> OfflineStdioClient:
            return self

        async def __aexit__(self, *exc: object) -> None:
            params = self.params
            assert hasattr(params, "env")
            environment = params.env
            assert environment is not None
            assert environment["CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS"] == "25"
            path = Path(environment["CAL_MCP_LIVE_SMOKE_REPORT_PATH"])
            path.write_text(
                json.dumps({"actual_cal_transport_attempts": 0,
                            "max_cal_transport_attempts": 25}),
                encoding="utf-8",
            )

    async def fake_cases(
        client: object,
        cases: tuple[SmokeCase, ...] = smoke.DEFAULT_SMOKE_CASES,
        *,
        min_cal_case_spacing_seconds: float = 0,
        **other: object,
    ) -> tuple[()]:
        del client, cases, other
        options.append(min_cal_case_spacing_seconds)
        return ()

    monkeypatch.setattr(smoke, "Client", OfflineStdioClient)
    monkeypatch.setattr(smoke, "evaluate_smoke_cases", fake_cases)
    outcomes, attempts = await _run_live("/no/network/cal-mcp")
    assert outcomes == ()
    assert attempts == 0
    assert options == [60.0]
