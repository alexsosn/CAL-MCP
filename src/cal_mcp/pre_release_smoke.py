"""Opt-in, bounded extra CAL MCP live smoke for independently sourced tool routes.

This diagnostic is NOT part of the published release's historical 13-case gate.
It must never be run on regular CI or scheduled; invoke only on an installed wheel.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError  # type: ignore[import-untyped]
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool

from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS
from cal_mcp.stdio_live_smoke import (
    SmokeCase,
    SmokeOutcome,
    _read_actual_attempts,
    evaluate_tool_result,
)

# Distinct, fixture-backed entry points. Dependent follow-ups belong in a
# separately reviewed batch with selectors taken from validated CAL results.
BATCH_CASES: tuple[SmokeCase, ...] = (
    SmokeCase("lexicon_browse", "cal_lexicon_browse", {"prefix": "br"}),
    SmokeCase("gloss_field", "cal_gloss_field", {"field": "medicine"}),
    SmokeCase("citation_text", "cal_citation_text_search", {"query": "camel"}),
    SmokeCase("text_catalogue", "cal_text_catalogue", {}),
    SmokeCase(
        "text_information",
        "cal_text_information",
        {"file_id": "6042013"},
        expected_statuses=("found",),
    ),
    SmokeCase(
        "token_analysis",
        "cal_token_analysis",
        {"coordinate": "7102601002203", "word_index": 0},
        expected_statuses=("found",),
    ),
    SmokeCase(
        "kwic_texts", "cal_kwic_texts", {"lemma_key": "mlk N", "text_ids": ["13250"]}
    ),
    SmokeCase("kwic_dialects", "cal_kwic_dialects", {"lemma_key": "mlk N"}),
    SmokeCase("bibliography_authors", "cal_bibliography_authors", {"prefix": "Kau"}),
    SmokeCase("targum_concordance", "cal_targum_concordance", {"lemma_key": "klb N"}),
    SmokeCase(
        "targum_hebrew_lemmas",
        "cal_targum_hebrew_lemmas",
        {"initial": "mem", "targum": "onqelos"},
    ),
    SmokeCase(
        "syriac_texts",
        "cal_syriac_texts",
        {"category": "metrical-homilies-hymns"},
    ),
    SmokeCase("syriac_missing", "cal_syriac_missing_words", {"category": "verbs"}),
)

# A schema-valid but empty success is not evidence that a positive fixture
# endpoint works. These keys are confirmed against model to_dict definitions.
REQUIRED_CONTENT_FIELDS: dict[str, str] = {
    "lexicon_browse": "rows",
    "gloss_field": "matches",
    "citation_text": "hits",
    "text_catalogue": "categories",
    "text_information": "metadata",
    "token_analysis": "candidates",
    "kwic_texts": "hits",
    "kwic_dialects": "dialects",
    "bibliography_authors": "candidates",
    "targum_concordance": "rows",
    "targum_hebrew_lemmas": "candidates",
    "syriac_texts": "items",
    "syriac_missing": "items",
}

_INTERVAL_SECONDS = 60.0
_MAX_ATTEMPTS = 25


def valid_registry(tools: Sequence[Tool]) -> bool:
    """Preflight ALL advertised output schemas before spending any CAL traffic."""
    names = [tool.name for tool in tools]
    if len(names) != len(set(names)) or set(names) != CURRENT_PUBLIC_TOOLS:
        return False
    for tool in tools:
        schema = tool.output_schema
        if not isinstance(schema, dict):
            return False
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError:
            return False
    return True


def valid_content(case: SmokeCase, payload: dict[str, object]) -> bool:
    """Require a positive, nonempty representative response for each fixed case."""
    key = REQUIRED_CONTENT_FIELDS.get(case.name)
    if key is None:
        return False
    items = payload.get(key)
    if not isinstance(items, list) or not items:
        return False
    for item in items:
        if isinstance(item, str):
            if not item.strip():
                return False
        elif isinstance(item, dict):
            if not any(
                (isinstance(value, str) and value.strip())
                or (type(value) is int and value >= 0)
                for value in item.values()
            ):
                return False
        else:
            return False
    if case.tool == "cal_token_analysis":
        return payload.get("status") == "found"
    if case.tool == "cal_text_information":
        return payload.get("status") == "found"
    return True


def terminal_backpressure(result: CallToolResult) -> bool:
    """Stop after actual CAL 429 or local admission exhaustion, without retries."""
    if not result.is_error or not isinstance(result.structured_content, dict):
        return False
    error = result.structured_content.get("error")
    return isinstance(error, dict) and (
        error.get("kind") == "local_rate_limit"
        or (error.get("kind") == "upstream_http" and error.get("status_code") == 429)
    )


def complete_batch(outcomes: tuple[SmokeOutcome, ...], actual_attempts: int) -> bool:
    """Fail closed on shortened, altered, repeated, or cache-only smoke results."""
    expected = tuple(case.name for case in BATCH_CASES)
    return (
        len(BATCH_CASES) == 13
        and len({case.tool for case in BATCH_CASES}) == 13
        and len(set(expected)) == 13
        and {case.tool for case in BATCH_CASES} <= CURRENT_PUBLIC_TOOLS
        and tuple(item.case for item in outcomes) == expected
        and all(item.category == "ok" for item in outcomes)
        and type(actual_attempts) is int
        and len(BATCH_CASES) <= actual_attempts <= _MAX_ATTEMPTS
    )


async def run_cases(
    client: Client,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[SmokeOutcome, ...]:
    """Sequential calls, independent selectors only, no continuation or retry."""
    try:
        listed = (await client.list_tools()).tools
    except Exception:
        return (SmokeOutcome("preflight", "harness", "cannot list installed tools"),)
    if not valid_registry(listed):
        return (SmokeOutcome("preflight", "harness", "incomplete or invalid registry"),)
    registry = {tool.name: tool for tool in listed}
    outcomes: list[SmokeOutcome] = []
    last_cal_finished: float | None = None
    for case in BATCH_CASES:
        if last_cal_finished is not None:
            remaining = _INTERVAL_SECONDS - (clock() - last_cal_finished)
            if remaining > 0:
                await sleep(remaining)
        try:
            result = await client.call_tool(case.tool, arguments=case.arguments)
        except Exception:
            outcomes.append(SmokeOutcome(case.name, "harness", "stdio MCP call failed"))
            break
        finally:
            last_cal_finished = clock()
        outcome = evaluate_tool_result(case, registry[case.tool], result)
        if (
            outcome.category == "ok"
            and isinstance(result.structured_content, dict)
            and not valid_content(case, result.structured_content)
        ):
            outcome = SmokeOutcome(case.name, "drift", "missing representative positive rows")
        outcomes.append(outcome)
        # Do not accumulate probes after drift or a transient upstream refusal.
        # The caller may inspect the sanitized result and decide on another run.
        if terminal_backpressure(result) or outcome.category != "ok":
            break
    return tuple(outcomes)


async def _run_live(executable: str) -> tuple[tuple[SmokeOutcome, ...], int]:
    with TemporaryDirectory(prefix="cal-mcp-extra-smoke-") as directory:
        count_file = Path(directory) / "attempts.json"
        env = dict(os.environ)
        env["CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS"] = str(_MAX_ATTEMPTS)
        env["CAL_MCP_LIVE_SMOKE_REPORT_PATH"] = str(count_file)
        async with Client(StdioServerParameters(command=executable, env=env)) as client:
            outcomes = await run_cases(client)
        return outcomes, _read_actual_attempts(count_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual bounded extra CAL MCP live smoke")
    parser.add_argument("--executable", help="absolute installed cal-mcp executable")
    args = parser.parse_args()
    executable = args.executable or shutil.which("cal-mcp")
    if not executable:
        print(json.dumps({"status": "failed", "category": "harness"}), file=sys.stderr)
        raise SystemExit(1)
    try:
        outcomes, attempts = asyncio.run(_run_live(executable))
    except Exception:
        print(json.dumps({"status": "failed", "category": "harness"}), file=sys.stderr)
        raise SystemExit(1) from None
    passed = complete_batch(outcomes, attempts)
    print(
        json.dumps(
            {
                "status": "passed" if passed else "failed",
                "actual_cal_transport_attempts": attempts,
                "max_cal_transport_attempts": _MAX_ATTEMPTS,
                "cases": [asdict(item) for item in outcomes],
            },
            sort_keys=True,
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
