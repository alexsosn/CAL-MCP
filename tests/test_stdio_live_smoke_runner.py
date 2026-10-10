from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.errors import PublicErrorKind, PublicToolError
from cal_mcp.stdio_live_smoke import SmokeCase, evaluate_smoke_cases


def _tool() -> Tool:
    return Tool(
        name="cal_lexicon_lookup",
        description="offline fixture",
        input_schema={"type": "object"},
        output_schema={
            "type": "object",
            "properties": {"status": {"type": "string"}},
            "required": ["status"],
        },
    )


def _result(data: dict[str, object], *, is_error: bool = False) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="untrusted HTML must not leak")],
        structured_content=data,
        is_error=is_error,
    )

def _error(kind: PublicErrorKind) -> dict[str, object]:
    return PublicToolError(
        kind=kind,
        operation="cal_lexicon_lookup",
        upstream_reached=True,
        retryable=False,
        message="synthetic CAL error",
        source_url="https://cal.huc.edu/cal_entry_web.php",
    ).to_dict()


def _unknown_error() -> dict[str, object]:
    payload = _error(PublicErrorKind.PARSER_DRIFT)
    error = payload["error"]
    assert isinstance(error, dict)
    error["kind"] = "unrecognized_budget_error"
    return payload


@dataclass
class FakeClient:
    results: list[CallToolResult]
    calls: list[str]

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(tools=[_tool()])

    async def call_tool(self, name: str, arguments: dict[str, object]) -> CallToolResult:
        assert arguments == {"query": "br"}
        self.calls.append(name)
        return self.results.pop(0)


@pytest.mark.anyio
async def test_stdio_cases_execute_sequentially_and_aggregate_independent_failures() -> None:
    client = FakeClient(
        results=[
            _result(_error(PublicErrorKind.PARSER_DRIFT), is_error=True),
            _result({"status": "found"}),
        ],
        calls=[],
    )
    cases = (
        SmokeCase("bad", "cal_lexicon_lookup", {"query": "br"}, needs_provenance=False),
        SmokeCase("good", "cal_lexicon_lookup", {"query": "br"}, needs_provenance=False),
    )
    outcome = await evaluate_smoke_cases(client, cases)  # type: ignore[arg-type]
    assert [x.category for x in outcome] == ["drift", "ok"]
    assert client.calls == ["cal_lexicon_lookup", "cal_lexicon_lookup"]
    assert all("HTML" not in x.message for x in outcome)


@pytest.mark.anyio
async def test_stdio_unknown_tool_error_stops_before_exhausting_server_budget() -> None:
    client = FakeClient(
        results=[
            _result(_unknown_error(), is_error=True),
            _result({"status": "found"}),
        ],
        calls=[],
    )
    cases = (
        SmokeCase("budget", "cal_lexicon_lookup", {"query": "br"}, needs_provenance=False),
        SmokeCase("must_skip", "cal_lexicon_lookup", {"query": "br"}, needs_provenance=False),
    )
    outcomes = await evaluate_smoke_cases(client, cases)  # type: ignore[arg-type]
    assert [x.category for x in outcomes] == ["harness"]
    assert client.calls == ["cal_lexicon_lookup"]
