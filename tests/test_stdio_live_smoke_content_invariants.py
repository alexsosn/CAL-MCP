"""Issue #157: representative CAL operations must not pass with empty valid JSON."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.bibliography import parse_bibliography_page
from cal_mcp.client import CalResponse
from cal_mcp.stdio_live_smoke import SmokeCase, evaluate_tool_result


def _evaluate(case_name: str, field: str, items: list[object]) -> str:
    tool = Tool(
        name="cal_test",
        description="offline shape test",
        input_schema={"type": "object"},
        output_schema={
            "type": "object",
            "properties": {field: {"type": "array"}},
            "required": [field],
        },
    )
    result = CallToolResult(
        content=[TextContent(type="text", text="")],
        structured_content={field: items},
        is_error=False,
    )
    case = SmokeCase(case_name, tool.name, {}, needs_provenance=False)
    return evaluate_tool_result(case, tool, result).category


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("bibliography", "records"),
        ("gloss", "matches"),
        ("text_concordance", "lemmas"),
        ("dictionary", "entries"),
        ("external_citations", "dialects"),
    ],
)
def test_schema_valid_empty_representative_results_are_drift(name: str, field: str) -> None:
    assert _evaluate(name, field, []) == "drift"


@pytest.mark.parametrize(
    ("name", "field", "items"),
    [
        ("bibliography", "records", [{"citation": "one"}]),
        ("gloss", "matches", [{"lemma_key": "mlk N"}]),
        ("text_concordance", "lemmas", [{"lemma_key": "mlk N", "cal_reports_no_data": False}]),
        ("dictionary", "entries", [{"display_lemma": "mlk"}]),
        ("external_citations", "dialects", [{"dialect_id": "x"}]),
    ],
)
def test_representative_results_require_minimum_rows(
    name: str, field: str, items: list[object]
) -> None:
    assert _evaluate(name, field, items) == "ok"


@pytest.mark.parametrize(
    ("name", "field", "items"),
    [
        ("bibliography", "records", [{"citation": ""}, {"citation": "second"}]),
        ("gloss", "matches", [{"lemma_key": ""}]),
        ("text_concordance", "lemmas", [{"cal_reports_no_data": True, "lemma_key": None}]),
        ("dictionary", "entries", [{"display_lemma": "   "}]),
        ("external_citations", "dialects", [{"dialect_id": ""}]),
    ],
)
def test_representative_results_require_usable_record_identity(
    name: str, field: str, items: list[object]
) -> None:
    assert _evaluate(name, field, items) == "drift"


def test_two_bibliography_records_with_citations_are_accepted() -> None:
    assert (
        _evaluate("bibliography", "records", [{"citation": "first"}, {"citation": "second"}])
        == "ok"
    )


def test_unrelated_smoke_cases_remain_generic_and_schema_checked() -> None:
    assert _evaluate("custom", "records", []) == "ok"


def test_real_cly_v_bibliography_fixture_is_a_valid_one_record_smoke_sample() -> None:
    """RED: fixture for the *selected* query contains one, not two, CAL works."""

    fixture = Path(__file__).parent / "fixtures" / "cal" / "bibliography_lemma_cly_v.html"
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getbiblemma.php?myauthor=cly+V",
        body=fixture.read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )
    page = parse_bibliography_page(response)
    assert len(page.records) == 1
    assert "Cognates Can Be Deceptive" in page.records[0].citation
    assert _evaluate(
        "bibliography",
        "records",
        [{"citation": record.citation} for record in page.records],
    ) == "ok"
