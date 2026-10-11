"""Issue #309: preflight MCP registry and stop on all harness failures.

Pure fake-stdio tests. These do not start a process or contact CAL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.stdio_live_smoke import SmokeCase, evaluate_smoke_cases


@dataclass
class FakeClient:
    available: tuple[str, ...]
    results: list[CallToolResult] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(
            tools=[
                Tool(
                    name=name,
                    description="offline fake",
                    input_schema={"type": "object"},
                    output_schema={
                        "type": "object",
                        "properties": {"status": {"type": "string"}},
                        "required": ["status"],
                    },
                )
                for name in self.available
            ]
        )

    async def call_tool(self, name: str, arguments: dict[str, object]) -> CallToolResult:
        del arguments
        self.calls.append(name)
        return self.results.pop(0)


def outcome(status: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="untrusted HTML never returned")],
        structured_content={"status": status},
        is_error=False,
    )


def case(name: str, tool: str = "cal_gloss_search", *, from_case: str | None = None) -> SmokeCase:
    return SmokeCase(
        name=name,
        tool=tool,
        arguments={"query": name},
        expected_statuses=("found",),
        needs_provenance=False,
        from_case=from_case,
    )


@pytest.mark.anyio
async def test_late_missing_required_tool_rejects_before_any_cal_call_or_wait() -> None:
    client = FakeClient(
        ("cal_gloss_search", "cal_text_concordance"),
        [outcome("found"), outcome("found")],
    )
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    cases = (
        case("first"),
        case("second", "cal_text_concordance"),
        case("last-missing", "cal_dictionary_collation"),
    )
    actual = await evaluate_smoke_cases(client, cases, min_cal_case_spacing_seconds=60, sleep=sleep)
    assert [(x.case, x.category, x.message) for x in actual] == [
        ("last-missing", "harness", "required public MCP tool missing")
    ]
    assert client.calls == []
    assert delays == []


@pytest.mark.anyio
async def test_registry_preflight_reports_first_missing_case_in_declared_order() -> None:
    client = FakeClient(("cal_gloss_search",), [outcome("found")])
    cases = (
        case("first"),
        case("missing-early", "cal_dictionary_collation"),
        case("missing-late", "cal_text_concordance"),
    )
    actual = await evaluate_smoke_cases(client, cases)
    assert [(x.case, x.category) for x in actual] == [("missing-early", "harness")]
    assert client.calls == []


@pytest.mark.anyio
async def test_unsupported_smoke_followup_harness_stops_later_cal_call() -> None:
    client = FakeClient(("cal_gloss_search",), [outcome("found"), outcome("found")])
    cases = (
        case("parent"),
        case("unsupported", from_case="parent"),
        case("should-not-call"),
    )
    actual = await evaluate_smoke_cases(client, cases)
    assert [(x.case, x.category, x.message) for x in actual] == [
        ("parent", "ok", "success"),
        ("unsupported", "harness", "unsupported smoke follow-up"),
    ]
    assert client.calls == ["cal_gloss_search"]


@pytest.mark.anyio
async def test_complete_registry_and_schema_valid_cal_drift_still_aggregate() -> None:
    client = FakeClient(
        ("cal_gloss_search", "cal_text_concordance"),
        [outcome("not_found"), outcome("found")],
    )
    actual = await evaluate_smoke_cases(
        client, (case("first"), case("second", "cal_text_concordance"))
    )
    assert [x.category for x in actual] == ["drift", "ok"]
    assert client.calls == ["cal_gloss_search", "cal_text_concordance"]


@pytest.mark.anyio
@pytest.mark.parametrize("bad_schema", [None, {"type": "not-a-valid-json-schema-type"}])
async def test_late_broken_mcp_output_schema_aborts_without_cal_traffic(
    bad_schema: dict[str, object] | None,
) -> None:
    class BrokenSchemaClient(FakeClient):
        async def list_tools(self) -> SimpleNamespace:
            registry = await super().list_tools()
            registry.tools = [
                tool.model_copy(update={"output_schema": bad_schema})
                if tool.name == "cal_text_concordance"
                else tool
                for tool in registry.tools
            ]
            return registry

    client = BrokenSchemaClient(
        ("cal_gloss_search", "cal_text_concordance"),
        [outcome("found"), outcome("found")],
    )
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    actual = await evaluate_smoke_cases(
        client,
        (case("first"), case("late-bad-schema", "cal_text_concordance")),
        min_cal_case_spacing_seconds=60,
        sleep=sleep,
    )
    assert [(x.case, x.category, x.message) for x in actual] == [
        (
            "late-bad-schema",
            "harness",
            "required public MCP output schema missing or invalid",
        )
    ]
    assert client.calls == []
    assert delays == []
