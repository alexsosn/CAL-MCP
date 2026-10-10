from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator
from mcp import Client
from mcp.types import CallToolResult, TextContent, Tool

from cal_mcp.errors import PublicErrorKind, PublicToolError
from cal_mcp.server import mcp
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
                "error": {"type": "object"},
            },
            "anyOf": [
                {"required": ["status", "provenance"]},
                {"required": ["error"]},
            ],
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
        typed_error = PublicToolError(
            kind=PublicErrorKind(kind),
            operation="cal_lexicon_lookup",
            upstream_reached=True,
            retryable=False,
            message="synthetic error",
        ).to_dict()
        result = evaluate_tool_result(_case(), _tool(), _result(typed_error, is_error=True))
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


@pytest.mark.anyio
async def test_real_mcp_error_schema_is_checked_before_drift_classification() -> None:
    # The public SDK schema deliberately admits structured errors via extra fields,
    # so the smoke runner also has to validate the typed error *contents*.
    async with Client(mcp, raise_exceptions=True) as client:
        tool = next(t for t in (await client.list_tools()).tools if t.name == "cal_lexicon_lookup")
    assert tool.output_schema is not None

    valid = PublicToolError(
        kind=PublicErrorKind.PARSER_DRIFT,
        operation="cal_lexicon_lookup",
        upstream_reached=True,
        retryable=False,
        message="synthetic fixture drift",
        source_url="https://cal.huc.edu/cal_entry_web.php",
    ).to_dict()
    assert Draft202012Validator(tool.output_schema).is_valid(valid)
    assert evaluate_tool_result(_case(), tool, _result(valid, is_error=True)).category == "drift"

    invalid_error_details = [
        {"error": {**valid["error"], "retryable": "yes"}},
        {"error": {key: value for key, value in valid["error"].items() if key != "operation"}},
        {"error": {**valid["error"], "operation": "cal_text_page"}},
        {"error": {**valid["error"], "kind": 123}},
    ]
    for malformed in invalid_error_details:
        # Current public output schema is permissive for errors; adapter must
        # reject malformed error envelopes before treating them as genuine drift.
        assert Draft202012Validator(tool.output_schema).is_valid(malformed)
        result = evaluate_tool_result(_case(), tool, _result(malformed, is_error=True))
        assert result.category == "harness"
        assert "untrusted upstream body" not in result.message
