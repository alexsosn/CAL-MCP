from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from mcp.types import CallToolResult, Tool

SmokeCategory = Literal["ok", "drift", "unavailable", "harness", "skipped_dependency"]


@dataclass(frozen=True, slots=True)
class SmokeCase:
    name: str
    tool: str
    arguments: dict[str, object]
    expected_statuses: tuple[str, ...] = ()
    needs_provenance: bool = True


@dataclass(frozen=True, slots=True)
class SmokeOutcome:
    case: str
    category: SmokeCategory
    message: str


def _valid_cal_origin(url: object) -> bool:
    if not isinstance(url, str) or any(not 0x21 <= ord(char) <= 0x7E for char in url):
        return False
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == "cal.huc.edu"
        and port is None
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def _valid_provenance(data: dict[str, object]) -> bool:
    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        return False
    source_url = provenance.get("source_url")
    raw_timestamp = provenance.get("retrieved_at")
    if not _valid_cal_origin(source_url) or not isinstance(raw_timestamp, str):
        return False
    try:
        parsed = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def evaluate_tool_result(case: SmokeCase, tool: Tool, result: CallToolResult) -> SmokeOutcome:
    """Inspect public MCP results without copying upstream HTML or error bodies into reports."""

    if case.tool != tool.name:
        return SmokeOutcome(case.name, "harness", "wrong tool selected")
    if result.is_error:
        content = result.structured_content
        error = content.get("error") if isinstance(content, dict) else None
        kind = error.get("kind") if isinstance(error, dict) else None
        if kind == "parser_drift":
            return SmokeOutcome(case.name, "drift", "CAL parser drift")
        if kind in {"network", "upstream_http", "content", "response_too_large"}:
            return SmokeOutcome(case.name, "unavailable", "CAL upstream unavailable or unsafe")
        return SmokeOutcome(case.name, "harness", "unclassified MCP tool failure")

    schema = tool.output_schema
    payload = result.structured_content
    if schema is None or not isinstance(payload, dict):
        return SmokeOutcome(case.name, "harness", "missing structured MCP output or schema")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)
    except (SchemaError, ValidationError):
        return SmokeOutcome(case.name, "harness", "MCP output schema mismatch")
    if case.expected_statuses and payload.get("status") not in case.expected_statuses:
        return SmokeOutcome(case.name, "drift", "unexpected CAL success status")
    if case.needs_provenance and not _valid_provenance(payload):
        return SmokeOutcome(case.name, "drift", "missing or untrusted CAL provenance")
    return SmokeOutcome(case.name, "ok", "success")
