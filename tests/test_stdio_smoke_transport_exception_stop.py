"""Issue #307: an uncertain/broken stdio call must stop further CAL-backed smoke probing.

Pure fake-client tests; zero CAL network or real subprocess I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.stdio_live_smoke import SmokeCase, evaluate_smoke_cases


@dataclass
class FakeClock:
    now: float = 100.0
    waits: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.waits.append(delay)
        self.now += delay


def _result(status: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="untrusted CAL HTML should never leak")],
        structured_content={"status": status},
        is_error=False,
    )


@dataclass
class FlakyStdioClient:
    scripted: list[CallToolResult | Exception]
    calls: list[str] = field(default_factory=list)

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(
            tools=[
                Tool(
                    name="cal_gloss_search",
                    description="offline fixture",
                    input_schema={"type": "object"},
                    output_schema={
                        "type": "object",
                        "properties": {"status": {"type": "string"}},
                        "required": ["status"],
                    },
                )
            ]
        )

    async def call_tool(self, name: str, arguments: dict[str, object]) -> CallToolResult:
        del arguments
        self.calls.append(name)
        response = self.scripted.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _cases() -> tuple[SmokeCase, ...]:
    return tuple(
        SmokeCase(
            f"cal-{i}",
            "cal_gloss_search",
            {"query": f"test-{i}"},
            expected_statuses=("found",),
            needs_provenance=False,
        )
        for i in range(3)
    )


@pytest.mark.anyio
async def test_transport_exception_on_first_smoke_case_stops_all_future_cal_calls() -> None:
    clock = FakeClock()
    client = FlakyStdioClient([ConnectionError("untrusted transport details"), _result("found")])
    outcomes = await evaluate_smoke_cases(
        client,
        _cases(),
        min_cal_case_spacing_seconds=60.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert [(o.case, o.category, o.message) for o in outcomes] == [
        ("cal-0", "harness", "MCP transport or schema error")
    ]
    assert client.calls == ["cal_gloss_search"]
    assert clock.waits == []


@pytest.mark.anyio
async def test_later_smoke_transport_exception_preserves_prior_drift_without_reprobe() -> None:
    clock = FakeClock()
    client = FlakyStdioClient(
        [_result("not_found"), RuntimeError("broken MCP channel"), _result("found")]
    )
    outcomes = await evaluate_smoke_cases(
        client,
        _cases(),
        min_cal_case_spacing_seconds=60.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert [(o.case, o.category) for o in outcomes] == [
        ("cal-0", "drift"),
        ("cal-1", "harness"),
    ]
    assert all("broken" not in o.message for o in outcomes)
    assert client.calls == ["cal_gloss_search"] * 2
    assert clock.waits == [60.0]


@pytest.mark.anyio
async def test_regular_cal_result_drift_still_aggregates_later_cases() -> None:
    clock = FakeClock()
    client = FlakyStdioClient([_result("not_found"), _result("found"), _result("not_found")])
    outcomes = await evaluate_smoke_cases(
        client,
        _cases(),
        min_cal_case_spacing_seconds=60.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert [o.category for o in outcomes] == ["drift", "ok", "drift"]
    assert client.calls == ["cal_gloss_search"] * 3
    assert clock.waits == [60.0, 60.0]


@pytest.mark.anyio
async def test_returned_mcp_output_schema_mismatch_stops_further_cal_probes() -> None:
    clock = FakeClock()
    malformed = CallToolResult(
        content=[TextContent(type="text", text="untrusted upstream body")],
        structured_content={"status": ["wrong structured type"]},
        is_error=False,
    )
    client = FlakyStdioClient([malformed, _result("found")])
    outcomes = await evaluate_smoke_cases(
        client,
        _cases(),
        min_cal_case_spacing_seconds=60.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert [(o.case, o.category, o.message) for o in outcomes] == [
        ("cal-0", "harness", "MCP output schema mismatch")
    ]
    assert client.calls == ["cal_gloss_search"]
    assert clock.waits == []
    assert "untrusted" not in outcomes[0].message
