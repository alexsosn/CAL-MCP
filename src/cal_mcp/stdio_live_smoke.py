from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError, ValidationError  # type: ignore[import-untyped]
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool

SmokeCategory = Literal["ok", "drift", "unavailable", "harness", "skipped_dependency"]

_ERROR_ENVELOPE_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["error"],
    "additionalProperties": False,
    "properties": {
        "error": {
            "type": "object",
            "required": [
                "kind",
                "operation",
                "upstream_reached",
                "retryable",
                "message",
                "source_url",
                "status_code",
            ],
            "additionalProperties": False,
            "properties": {
                "kind": {
                    "enum": [
                        "invalid_input",
                        "network",
                        "upstream_http",
                        "response_too_large",
                        "content",
                        "parser_drift",
                    ]
                },
                "operation": {"type": "string"},
                "upstream_reached": {"type": ["boolean", "null"]},
                "retryable": {"type": "boolean"},
                "message": {"type": "string", "minLength": 1, "maxLength": 500},
                "source_url": {"type": ["string", "null"]},
                "status_code": {"type": ["integer", "null"], "minimum": 100, "maximum": 599},
            },
        }
    },
}
_ERROR_ENVELOPE_VALIDATOR = Draft202012Validator(_ERROR_ENVELOPE_SCHEMA)


@dataclass(frozen=True, slots=True)
class SmokeCase:
    name: str
    tool: str
    arguments: dict[str, object]
    expected_statuses: tuple[str, ...] = ()
    needs_provenance: bool = True
    from_case: str | None = None


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


def _has_representative_content(case_name: str, data: dict[str, object]) -> bool:
    """Require the studied reference queries to contain recognizable scholarly rows."""

    field_by_case = {
        "bibliography": ("records", "citation", 2),
        "gloss": ("matches", "lemma_key", 1),
        "text_concordance": ("lemmas", "lemma_key", 1),
        "dictionary": ("entries", "display_lemma", 1),
        "external_citations": ("dialects", "dialect_id", 1),
    }
    expected = field_by_case.get(case_name)
    if expected is None:
        return True
    field, identity, minimum = expected
    rows = data.get(field)
    if not isinstance(rows, list) or len(rows) < minimum:
        return False
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get(identity), str)
        or not row[identity].strip()
        for row in rows
    ):
        return False
    return case_name != "text_concordance" or any(
        row.get("cal_reports_no_data") is False for row in rows
    )


def evaluate_tool_result(case: SmokeCase, tool: Tool, result: CallToolResult) -> SmokeOutcome:
    """Inspect public MCP results without copying upstream HTML or error bodies into reports."""

    if case.tool != tool.name:
        return SmokeOutcome(case.name, "harness", "wrong tool selected")
    schema = tool.output_schema
    payload = result.structured_content
    if schema is None or not isinstance(payload, dict):
        return SmokeOutcome(case.name, "harness", "missing structured MCP output or schema")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)
    except (SchemaError, ValidationError):
        return SmokeOutcome(case.name, "harness", "MCP output schema mismatch")

    if result.is_error:
        if not _ERROR_ENVELOPE_VALIDATOR.is_valid(payload):
            return SmokeOutcome(case.name, "harness", "malformed MCP structured error")
        error = payload["error"]
        if error["operation"] != case.tool or (
            error["source_url"] is not None and not _valid_cal_origin(error["source_url"])
        ):
            return SmokeOutcome(case.name, "harness", "untrusted MCP error identity or source")
        kind = error["kind"]
        if kind == "parser_drift":
            return SmokeOutcome(case.name, "drift", "CAL parser drift")
        if kind in {"network", "upstream_http", "content", "response_too_large"}:
            return SmokeOutcome(case.name, "unavailable", "CAL upstream unavailable or unsafe")
        return SmokeOutcome(case.name, "harness", "unclassified MCP tool failure")

    if case.expected_statuses and payload.get("status") not in case.expected_statuses:
        return SmokeOutcome(case.name, "drift", "unexpected CAL success status")
    if case.needs_provenance and not _valid_provenance(payload):
        return SmokeOutcome(case.name, "drift", "missing or untrusted CAL provenance")
    if not _has_representative_content(case.name, payload):
        return SmokeOutcome(case.name, "drift", "missing representative CAL result rows")
    return SmokeOutcome(case.name, "ok", "success")


# All cases are fixed and sequential; one server subprocess enforces 25 actual
# upstream attempts across the *entire* matrix. Never enumerate returned pages.
DEFAULT_SMOKE_CASES: tuple[SmokeCase, ...] = (
    SmokeCase("conversion", "cal_convert_to_code", {"value": "ܫܠ"}, needs_provenance=False),
    SmokeCase(
        "lexicon_noun", "cal_lexicon_lookup", {"query": "br", "lemma_key": "br N"}, ("found",)
    ),
    SmokeCase(
        "lexicon_verb", "cal_lexicon_lookup", {"query": "ktb", "lemma_key": "ktb V"}, ("found",)
    ),
    SmokeCase("gloss", "cal_gloss_search", {"query": "king"}),
    SmokeCase("text_search", "cal_text_search", {"query": "Tel Dan"}),
    SmokeCase(
        "text_page_followup",
        "cal_text_page",
        {},
        ("found",),
        from_case="text_search",
    ),
    SmokeCase("text_concordance", "cal_text_concordance", {"text_id": "13250"}),
    SmokeCase("bibliography", "cal_bibliography_lemma", {"lemma_key": "cly V"}),
    SmokeCase("dictionary", "cal_dictionary_collation", {"source": "jastrow", "page": "705"}),
    SmokeCase("external_citations", "cal_external_citation_dialects", {}),
    SmokeCase(
        "targum", "cal_targum_parallel", {"book": "Gen", "chapter": 1, "verse": 1}, ("found",)
    ),
    SmokeCase(
        "peshitta",
        "cal_syriac_peshitta_parallel",
        {"book": "Gen", "chapter": 1, "verse": 1},
        ("found",),
    ),
)


def _select_one_direct_text_page(parent: dict[str, object]) -> dict[str, object] | None:
    """Choose at most one CAL-declared page target, preserving its exact selectors."""

    matches = parent.get("matches")
    if not isinstance(matches, list):
        return None
    for match in matches:
        if not isinstance(match, dict) or match.get("follow_up_tool") != "cal_text_page":
            continue
        file_id = match.get("file_id")
        subtext_id = match.get("subtext_id")
        if (
            match.get("category_id") is not None
            or type(file_id) is not str
            or re.fullmatch(r"[0-9]+", file_id) is None
            or (
                subtext_id is not None
                and (
                    type(subtext_id) is not str or re.fullmatch(r"[0-9]+[a-z]?", subtext_id) is None
                )
            )
        ):
            return None
        return {"file_id": file_id, "subtext_id": subtext_id, "page": 1}
    return None


async def evaluate_smoke_cases(
    client: Client,
    cases: tuple[SmokeCase, ...] = DEFAULT_SMOKE_CASES,
) -> tuple[SmokeOutcome, ...]:
    """Run known operations in order, collecting sanitized failures without unbounded follow-up."""

    listed = {tool.name: tool for tool in (await client.list_tools()).tools}
    outcomes: list[SmokeOutcome] = []
    successful: dict[str, dict[str, object]] = {}
    for case in cases:
        tool = listed.get(case.tool)
        if tool is None:
            outcomes.append(SmokeOutcome(case.name, "harness", "required public MCP tool missing"))
            continue
        arguments = case.arguments
        if case.from_case is not None:
            parent = successful.get(case.from_case)
            if parent is None:
                outcomes.append(
                    SmokeOutcome(case.name, "skipped_dependency", "parent case did not pass")
                )
                continue
            if case.tool != "cal_text_page":
                outcomes.append(SmokeOutcome(case.name, "harness", "unsupported smoke follow-up"))
                continue
            selected = _select_one_direct_text_page(parent)
            if selected is None:
                outcomes.append(SmokeOutcome(case.name, "drift", "no trusted direct text selector"))
                continue
            arguments = selected
        try:
            result = await client.call_tool(case.tool, arguments=arguments)
        except Exception:
            outcomes.append(SmokeOutcome(case.name, "harness", "MCP transport or schema error"))
            continue
        outcome = evaluate_tool_result(case, tool, result)
        outcomes.append(outcome)
        if outcome.category == "ok" and isinstance(result.structured_content, dict):
            successful[case.name] = result.structured_content
        if outcome.category == "harness" and outcome.message in {
            "unclassified MCP tool failure",
            "missing structured MCP output or schema",
            "malformed MCP structured error",
            "untrusted MCP error identity or source",
        }:
            # A failed or unrecognized error channel may mean that the bounded server
            # has exhausted its budget. Stop rather than repeatedly calling a broken
            # process; ordinary schema/provenance drift can still be aggregated.
            break
    return tuple(outcomes)


def _read_actual_attempts(report_path: Path) -> int:
    """Only accept a complete measured count from the terminated smoke server."""

    try:
        contents = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("installed smoke server did not report actual attempts") from error
    if (
        not isinstance(contents, dict)
        or set(contents) != {"actual_cal_transport_attempts", "max_cal_transport_attempts"}
        or type(contents.get("max_cal_transport_attempts")) is not int
        or contents["max_cal_transport_attempts"] != 25
        or type(contents.get("actual_cal_transport_attempts")) is not int
        or not 0 <= contents["actual_cal_transport_attempts"] <= 25
    ):
        raise ValueError("installed smoke server reported an invalid transport attempt count")
    return int(contents["actual_cal_transport_attempts"])


async def _run_live(executable: str) -> tuple[tuple[SmokeOutcome, ...], int]:
    with TemporaryDirectory(prefix="cal-mcp-stdio-smoke-") as directory:
        count_file = Path(directory) / "attempts.json"
        env = dict(os.environ)
        env["CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS"] = "25"
        env["CAL_MCP_LIVE_SMOKE_REPORT_PATH"] = str(count_file)
        async with Client(StdioServerParameters(command=executable, env=env)) as client:
            outcomes = await evaluate_smoke_cases(client)
        return outcomes, _read_actual_attempts(count_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded installed CAL-MCP stdio live smoke")
    parser.add_argument("--executable", help="exact installed cal-mcp executable on PATH")
    arguments = parser.parse_args()
    executable = arguments.executable or shutil.which("cal-mcp")
    if not executable:
        print(json.dumps({"status": "failed", "category": "harness"}), file=sys.stderr)
        raise SystemExit(1)

    try:
        outcomes, actual_attempts = asyncio.run(_run_live(executable))
    except Exception:
        print(json.dumps({"status": "failed", "category": "harness"}), file=sys.stderr)
        raise SystemExit(1) from None

    successful = all(item.category == "ok" for item in outcomes)
    report = {
        "status": "passed" if successful else "failed",
        "max_cal_transport_attempts": 25,
        "actual_cal_transport_attempts": actual_attempts,
        "cases": [asdict(item) for item in outcomes],
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if not successful:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
