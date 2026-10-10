"""Offline returned-selector chain tests for issue #157; never contact CAL."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.stdio_live_smoke import SmokeCase, evaluate_smoke_cases


def _result(data: dict[str, object], *, is_error: bool = False) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="do not copy CAL HTML")],
        structured_content=data,
        is_error=is_error,
    )


@dataclass
class FakeClient:
    results: list[CallToolResult]
    calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(
            tools=[
                Tool(
                    name="cal_text_search",
                    description="test search",
                    input_schema={"type": "object"},
                    output_schema={
                        "type": "object",
                        "properties": {"matches": {"type": "array"}},
                        "required": ["matches"],
                    },
                ),
                Tool(
                    name="cal_text_page",
                    description="test page",
                    input_schema={"type": "object"},
                    output_schema={
                        "type": "object",
                        "properties": {"status": {"type": "string"}},
                        "required": ["status"],
                    },
                ),
            ]
        )

    async def call_tool(self, name: str, arguments: dict[str, object]) -> CallToolResult:
        self.calls.append((name, arguments))
        return self.results.pop(0)


CASES = (
    SmokeCase("search", "cal_text_search", {"query": "Tel Dan"}, needs_provenance=False),
    SmokeCase(
        "page_followup",
        "cal_text_page",
        {},
        expected_statuses=("found",),
        needs_provenance=False,
        from_case="search",
    ),
)


def _match(file_id: object, subtext_id: object = None) -> dict[str, object]:
    return {
        "file_id": file_id,
        "subtext_id": subtext_id,
        "category_id": None,
        "follow_up_tool": "cal_text_page",
    }


@pytest.mark.anyio
async def test_stdio_followup_uses_returned_direct_text_selectors_exactly_once() -> None:
    client = FakeClient(
        [
            _result(
                {
                    "matches": [
                        {
                            "file_id": None,
                            "category_id": "54001",
                            "follow_up_tool": "cal_text_catalogue",
                        },
                        _match("13250", "001a"),
                        _match("88888"),
                    ]
                }
            ),
            _result({"status": "found"}),
        ]
    )
    outcomes = await evaluate_smoke_cases(client, CASES)  # type: ignore[arg-type]
    assert [x.category for x in outcomes] == ["ok", "ok"]
    assert client.calls == [
        ("cal_text_search", {"query": "Tel Dan"}),
        ("cal_text_page", {"file_id": "13250", "subtext_id": "001a", "page": 1}),
    ]


@pytest.mark.anyio
async def test_stdio_failed_parent_skips_followup_without_transport() -> None:
    client = FakeClient([_result({"status": "unrecognized"})])
    outcomes = await evaluate_smoke_cases(client, CASES)  # type: ignore[arg-type]
    assert [x.category for x in outcomes] == ["harness", "skipped_dependency"]
    assert len(client.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    "matches",
    [
        [],
        [{"file_id": None, "category_id": "54001", "follow_up_tool": "cal_text_catalogue"}],
        [_match("../escape")],
        [_match(13250)],
        [_match("13250", "&unsafe")],
    ],
)
async def test_stdio_missing_or_untrusted_direct_match_is_drift_without_followup(
    matches: list[dict[str, object]],
) -> None:
    client = FakeClient([_result({"matches": matches})])
    outcomes = await evaluate_smoke_cases(client, CASES)  # type: ignore[arg-type]
    assert [x.category for x in outcomes] == ["ok", "drift"]
    assert len(client.calls) == 1
