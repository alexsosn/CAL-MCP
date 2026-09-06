from __future__ import annotations

from types import SimpleNamespace

import pytest


def _result(
    *,
    is_error: bool = False,
    structured_content: object | None = None,
    text: str = "",
) -> SimpleNamespace:
    content = [SimpleNamespace(text=text)] if text else []
    return SimpleNamespace(
        is_error=is_error,
        structured_content=structured_content,
        content=content,
    )


def test_live_smoke_accepts_success_with_cal_provenance() -> None:
    from cal_mcp.live_smoke import validate_tool_result

    result = _result(
        structured_content={
            "status": "found",
            "provenance": {
                "source_url": "https://cal.huc.edu/showtargum.php",
                "retrieved_at": "2026-09-06T00:00:00+00:00",
            },
        }
    )

    validate_tool_result("cal_targum_parallel", result)


def test_live_smoke_rejects_mcp_error_result() -> None:
    from cal_mcp.live_smoke import SmokeFailure, validate_tool_result

    with pytest.raises(SmokeFailure) as exc_info:
        validate_tool_result(
            "cal_text_concordance",
            _result(is_error=True, text="Error executing tool cal_text_concordance"),
        )

    assert exc_info.value.kind == "adapter_or_parser_drift"
    assert exc_info.value.tool_name == "cal_text_concordance"


def test_live_smoke_rejects_success_without_structured_provenance() -> None:
    from cal_mcp.live_smoke import SmokeFailure, validate_tool_result

    with pytest.raises(SmokeFailure) as exc_info:
        validate_tool_result("cal_text_search", _result(structured_content={"results": []}))

    assert exc_info.value.kind == "adapter_or_parser_drift"


def test_live_smoke_classifies_upstream_unavailability() -> None:
    from cal_mcp.client import CalNetworkError, CalUpstreamError
    from cal_mcp.live_smoke import classify_fetch_failure

    assert classify_fetch_failure(CalNetworkError("network unavailable")) == "upstream_unavailable"
    assert (
        classify_fetch_failure(CalUpstreamError(503, "https://cal.huc.edu/example"))
        == "upstream_unavailable"
    )
    assert (
        classify_fetch_failure(CalUpstreamError(404, "https://cal.huc.edu/example"))
        == "adapter_or_parser_drift"
    )
    assert classify_fetch_failure(ValueError("changed parser shape")) == "adapter_or_parser_drift"


def test_live_smoke_budget_rejects_tenth_request_before_issue() -> None:
    from cal_mcp.live_smoke import RequestBudget, SmokeBudgetExceeded

    budget = RequestBudget(max_requests=9)
    for _ in range(9):
        budget.claim()

    assert budget.request_count == 9
    with pytest.raises(SmokeBudgetExceeded):
        budget.claim()
    assert budget.request_count == 9


def test_live_smoke_cases_are_fixed_and_bounded() -> None:
    from cal_mcp.live_smoke import MAX_CAL_REQUESTS, SMOKE_CASES

    assert MAX_CAL_REQUESTS == 9
    assert [case.tool_name for case in SMOKE_CASES] == [
        "cal_lexicon_lookup",
        "cal_text_search",
        "cal_text_concordance",
        "cal_bibliography_lemma",
        "cal_dictionary_collation",
        "cal_external_citation_dialects",
        "cal_targum_parallel",
        "cal_syriac_peshitta_parallel",
    ]
    assert len(SMOKE_CASES) == 8
