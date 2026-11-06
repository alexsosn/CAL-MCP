"""Issue #330: current release smoke must gate the post-v0.1 bibliography operation.

These are entirely offline synthetic MCP contract tests. Research and plan precede RED.
"""

from __future__ import annotations

import pytest
from mcp.types import CallToolResult, TextContent, Tool

import cal_mcp.stdio_live_smoke as smoke


def _successful_outcomes() -> tuple[smoke.SmokeOutcome, ...]:
    return tuple(
        smoke.SmokeOutcome(case.name, "ok", "success") for case in smoke.DEFAULT_SMOKE_CASES
    )


def test_current_release_has_exactly_one_new_researched_case_after_v01() -> None:
    cases = smoke.DEFAULT_SMOKE_CASES
    assert len(smoke._REVIEWED_V01_SMOKE_IDENTITIES) == 12
    assert len(cases) == 13
    assert [case.name for case in cases][-1] == "recent_bibliography"
    assert cases[-1] == smoke.SmokeCase(
        "recent_bibliography", "cal_bibliography_recent", {}
    )
    assert len({case.name for case in cases}) == 13
    assert sum(case.tool != "cal_convert_to_code" for case in cases) == 12
    assert (
        *smoke._REVIEWED_V01_SMOKE_IDENTITIES,
        ("recent_bibliography", "cal_bibliography_recent", (), (), True, None),
    ) == smoke._REVIEWED_CURRENT_SMOKE_IDENTITIES


def test_current_full_success_requires_twelve_actual_cal_starts() -> None:
    complete = _successful_outcomes()
    assert not smoke._complete_release_smoke_matrix(complete, 11)
    assert smoke._complete_release_smoke_matrix(complete, 12)
    assert smoke._complete_release_smoke_matrix(complete, 25)
    assert not smoke._complete_release_smoke_matrix(complete, 26)


def test_original_v01_only_matrix_cannot_authorize_current_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = smoke.DEFAULT_SMOKE_CASES
    assert len(cases) == 13
    monkeypatch.setattr(smoke, "DEFAULT_SMOKE_CASES", cases[:-1])
    historical = tuple(
        smoke.SmokeOutcome(case.name, "ok", "success") for case in cases[:-1]
    )
    assert not smoke._complete_release_smoke_matrix(historical, 12)


def _recent_result(records: list[object]) -> str:
    tool = Tool(
        name="cal_bibliography_recent",
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {"records": {"type": "array"}},
            "required": ["records"],
        },
    )
    response = CallToolResult(
        content=[TextContent(type="text", text="")],
        structured_content={"records": records},
        is_error=False,
    )
    case = smoke.SmokeCase(
        "recent_bibliography", "cal_bibliography_recent", {}, needs_provenance=False
    )
    return smoke.evaluate_tool_result(case, tool, response).category


@pytest.mark.parametrize(
    "records",
    [
        [],
        [{}],
        ["unstructured"],
        [{"citation": ""}],
        [{"citation": "   "}],
        [{"citation": "one"}, {"citation": ""}],
        [{"citation": 42}],
    ],
)
def test_recent_bibliography_empty_or_invalid_citations_fail_smoke(
    records: list[object],
) -> None:
    assert _recent_result(records) == "drift"


def test_recent_bibliography_nonempty_citations_are_valid_smoke_content() -> None:
    assert _recent_result([{"citation": "first"}, {"citation": "second"}]) == "ok"
