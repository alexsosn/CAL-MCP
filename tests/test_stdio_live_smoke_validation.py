from __future__ import annotations

from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.stdio_live_smoke import SmokeCase, evaluate_tool_result


def _tool() -> Tool:
    return Tool(
        name="cal_lexicon_lookup",
        description="test tool",
        input_schema={"type": "object"},
        output_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "provenance": {"type": "object"},
            },
            "required": ["status", "provenance"],
        },
    )


def _result(data: dict[str, object], *, is_error: bool = False) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="<script>untrusted upstream body</script>")],
        structured_content=data,
        is_error=is_error,
    )


def _case() -> SmokeCase:
    return SmokeCase(
        name="lexicon",
        tool="cal_lexicon_lookup",
        arguments={"query": "br", "lemma_key": "br N"},
        expected_statuses=("found",),
    )


def _provenance() -> dict[str, str]:
    return {
        "source_url": "https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
        "retrieved_at": "2026-10-10T09:00:00+00:00",
    }


def test_stdio_success_requires_declared_schema_and_trusted_cal_provenance() -> None:
    result = evaluate_tool_result(
        _case(), _tool(), _result({"status": "found", "provenance": _provenance()})
    )
    assert result.category == "ok"


def test_stdio_schema_violation_is_harness_failure_without_echoing_html() -> None:
    result = evaluate_tool_result(
        _case(), _tool(), _result({"status": ["found"], "provenance": _provenance()})
    )
    assert result.category == "harness"
    assert "untrusted upstream body" not in result.message


def test_stdio_source_url_cannot_escape_exact_cal_origin() -> None:
    provenance = _provenance()
    provenance["source_url"] = "https://cal.huc.edu.evil.invalid/"
    result = evaluate_tool_result(
        _case(), _tool(), _result({"status": "found", "provenance": provenance})
    )
    assert result.category == "drift"


def test_stdio_parser_drift_and_network_errors_are_not_confused() -> None:
    for kind, expected in (("parser_drift", "drift"), ("network", "unavailable")):
        result = evaluate_tool_result(
            _case(), _tool(), _result({"error": {"kind": kind}}, is_error=True)
        )
        assert result.category == expected
        assert "untrusted upstream body" not in result.message


def test_stdio_missing_declared_output_schema_is_harness_failure() -> None:
    tool = _tool().model_copy(update={"output_schema": None})
    result = evaluate_tool_result(
        _case(), tool, _result({"status": "found", "provenance": _provenance()})
    )
    assert result.category == "harness"


def test_stdio_unexpected_found_status_is_reported_as_drift() -> None:
    result = evaluate_tool_result(
        _case(), _tool(), _result({"status": "not_found", "provenance": _provenance()})
    )
    assert result.category == "drift"
