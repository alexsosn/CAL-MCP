"""Manual installed-wheel smoke for CAL MCP follow-ups using returned typed selectors.

No implicit enumeration, guessed IDs, scheduled runs, or CAL content in reports.
Run only after the preceding independent-tool batch has stopped.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult

from cal_mcp.pre_release_smoke import terminal_backpressure, valid_registry
from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS
from cal_mcp.stdio_live_smoke import (
    SmokeCase,
    SmokeOutcome,
    _read_actual_attempts,
    evaluate_tool_result,
)


@dataclass(frozen=True, slots=True)
class FollowupStep:
    name: str
    tool: str
    arguments: dict[str, object] | None = None
    parent: str | None = None
    positive_field: str = ""
    expected_statuses: tuple[str, ...] = ()


# Each dependent operation consumes exactly one already-validated prior result.
# The nine explicit selector operations are independent bounded CAL calls.
STEPS: tuple[FollowupStep, ...] = (
    FollowupStep(
        "lexicon",
        "cal_lexicon_lookup",
        {"query": "br", "lemma_key": "br N"},
        positive_field="entry",
        expected_statuses=("found",),
    ),
    FollowupStep(
        "lexicon_context",
        "cal_lexicon_citation_context",
        parent="lexicon",
        positive_field="lines",
        expected_statuses=("found",),
    ),
    FollowupStep(
        "text_page",
        "cal_text_page",
        {"file_id": "13250", "page": 1},
        positive_field="page",
        expected_statuses=("found",),
    ),
    FollowupStep(
        "text_comments",
        "cal_text_line_comments",
        parent="text_page",
        positive_field="records",
        expected_statuses=("found",),
    ),
    FollowupStep(
        "kwic_dialects_selector",
        "cal_kwic_dialects",
        {"lemma_key": ")ryk#2 A"},
        positive_field="dialects",
    ),
    FollowupStep(
        "kwic_dialect",
        "cal_kwic_dialect",
        parent="kwic_dialects_selector",
        positive_field="hits",
    ),
    FollowupStep(
        "kwic_hits",
        "cal_kwic_texts",
        {"lemma_key": "mlk N", "text_ids": ["13250"]},
        positive_field="hits",
    ),
    FollowupStep(
        "kwic_context",
        "cal_kwic_full_context",
        parent="kwic_hits",
        positive_field="lines",
        expected_statuses=("found",),
    ),
    FollowupStep(
        "authors",
        "cal_bibliography_authors",
        {"prefix": "Kau"},
        positive_field="candidates",
    ),
    FollowupStep(
        "bibliography_author",
        "cal_bibliography_author",
        parent="authors",
        positive_field="records",
    ),
    FollowupStep(
        "bibliography_keyword",
        "cal_bibliography_keyword",
        parent="bibliography_author",
        positive_field="records",
    ),
    FollowupStep(
        "targum_concordance_followup",
        "cal_targum_concordance",
        {"lemma_key": "klb N"},
        positive_field="rows",
    ),
    FollowupStep(
        "targum_examples",
        "cal_targum_concordance_examples",
        parent="targum_concordance_followup",
        positive_field="hits",
    ),
    FollowupStep(
        "hebrew_lemmas",
        "cal_targum_hebrew_lemmas",
        {"initial": "mem", "targum": "onqelos"},
        positive_field="candidates",
    ),
    FollowupStep(
        "targum_reflex",
        "cal_targum_hebrew_reflexes",
        parent="hebrew_lemmas",
        positive_field="reflexes",
    ),
    FollowupStep(
        "targum_reflex_examples",
        "cal_targum_reflex_examples",
        parent="targum_reflex",
        positive_field="examples",
    ),
    FollowupStep(
        "external_dialects",
        "cal_external_citation_dialects",
        {},
        positive_field="dialects",
    ),
    FollowupStep(
        "external_sources",
        "cal_external_citation_sources",
        parent="external_dialects",
        positive_field="sources",
    ),
    FollowupStep(
        "external_citation_records",
        "cal_external_citations",
        parent="external_sources",
        positive_field="citations",
    ),
    FollowupStep(
        "syriac_category",
        "cal_syriac_texts",
        {"category": "metrical-homilies-hymns"},
        positive_field="items",
    ),
    FollowupStep(
        "syriac_group",
        "cal_syriac_group",
        parent="syriac_category",
        positive_field="items",
    ),
)
STEP_BY_NAME = {step.name: step for step in STEPS}
# Safe continuation after the recorded Tel Dan comment parser drift in #343.
# This is an evidence-gathering subset and can never certify the original full batch.
REMAINDER_STEPS: tuple[FollowupStep, ...] = STEPS[4:]
SYRIAC_STEPS: tuple[FollowupStep, ...] = STEPS[-2:]
EXTERNAL_STEPS: tuple[FollowupStep, ...] = STEPS[-5:-2]
_REVIEWED_REMAINDER_NAMES = (
    "kwic_dialects_selector",
    "kwic_dialect",
    "kwic_hits",
    "kwic_context",
    "authors",
    "bibliography_author",
    "bibliography_keyword",
    "targum_concordance_followup",
    "targum_examples",
    "hebrew_lemmas",
    "targum_reflex",
    "targum_reflex_examples",
    "external_dialects",
    "external_sources",
    "external_citation_records",
    "syriac_category",
    "syriac_group",
)
TARGET_TOOLS = frozenset(
    {
        "cal_lexicon_citation_context",
        "cal_text_line_comments",
        "cal_kwic_dialect",
        "cal_kwic_full_context",
        "cal_bibliography_author",
        "cal_bibliography_keyword",
        "cal_targum_concordance_examples",
        "cal_targum_hebrew_reflexes",
        "cal_targum_reflex_examples",
        "cal_external_citation_sources",
        "cal_external_citations",
        "cal_syriac_group",
    }
)
_INTERVAL_SECONDS = 60.0
_MAX_ATTEMPTS = 25


def _objects(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    return [cast(dict[str, object], item) for item in raw if isinstance(item, dict)]


def _text(value: object) -> str | None:
    if isinstance(value, str) and value and value.isascii() and value.isprintable():
        return value
    return None


def _positive_decimal(value: object) -> str | None:
    text = _text(value)
    if text is not None and text.isdecimal() and int(text) > 0:
        return text
    return None


def select_arguments(
    step: FollowupStep, successful: dict[str, dict[str, object]]
) -> dict[str, object] | None:
    """Only take opaque selectors from the already schema-validated parent payload."""
    if step.parent is None:
        return step.arguments
    parent = successful.get(step.parent)
    if parent is None:
        return None
    if step.name == "lexicon_context":
        entry = parent.get("entry")
        if isinstance(entry, dict):
            for sense in _objects(entry.get("senses")):
                for citation in _objects(sense.get("citations")):
                    coordinate = _positive_decimal(citation.get("full_coordinate"))
                    if coordinate:
                        return {"full_coordinate": coordinate}
    elif step.name == "text_comments":
        page = parent.get("page")
        if isinstance(page, dict):
            for line in _objects(page.get("lines")):
                coordinate = _text(line.get("coordinate"))
                if (
                    coordinate is not None
                    and 1 <= len(coordinate) <= 64
                    and coordinate.isalnum()
                    and line.get("comment_url")
                    == f"https://cal.huc.edu/comment.php?coord={coordinate}"
                ):
                    return {"coordinate": coordinate}
    elif step.name == "kwic_dialect":
        for row in _objects(parent.get("dialects")):
            dialect = _positive_decimal(row.get("dialect_id"))
            if dialect == "3":  # Source-backed Biblical Aramaic positive fixture.
                return {"lemma_key": ")ryk#2 A", "dialect_id": dialect}
    elif step.name == "kwic_context":
        for hit in _objects(parent.get("hits")):
            file_id = _positive_decimal(hit.get("file_id"))
            target = _text(hit.get("target_coordinate"))
            charset = _text(hit.get("charset"))
            if (
                file_id is not None
                and target is not None
                and target.isalnum()
                and charset in {"R", "H", "S", "T", "U"}
            ):
                args: dict[str, object] = {
                    "file_id": file_id,
                    "target_coordinate": target,
                    "charset": charset,
                }
                subtext_id = hit.get("subtext_id")
                if subtext_id is not None:
                    subtext = _text(subtext_id)
                    if subtext is None or not subtext.isalnum():
                        continue
                    args["subtext_id"] = subtext
                return args
    elif step.name == "bibliography_author":
        for row in _objects(parent.get("candidates")):
            value = _text(row.get("value"))
            if value == "Kaufman, Stephen A.":
                return {"author": value}
    elif step.name == "bibliography_keyword":
        for record in _objects(parent.get("records")):
            for link in _objects(record.get("links")):
                value = _text(link.get("query_value"))
                if link.get("query_kind") == "keyword" and value:
                    return {"keyword": value}
    elif step.name == "targum_examples":
        for row in _objects(parent.get("rows")):
            identifiers = row.get("text_ids")
            if isinstance(identifiers, list):
                ids = [_positive_decimal(item) for item in identifiers]
                if ids and all(ids) and len(ids) <= 8:
                    return {"lemma_key": "klb N", "text_ids": ids}
    elif step.name == "targum_reflex":
        for row in _objects(parent.get("candidates")):
            key = _positive_decimal(row.get("mt_lemma_id"))
            if key == "1751":
                return {"targum": "onqelos", "mt_lemma_id": key}
    elif step.name == "targum_reflex_examples":
        targum = _text(parent.get("targum"))
        mt_id = _positive_decimal(parent.get("mt_lemma_id"))
        for row in _objects(parent.get("reflexes")):
            lemma_key = _text(row.get("lemma_key"))
            if targum == "onqelos" and mt_id == "1751" and lemma_key == "tyq#2 N":
                return {"targum": targum, "mt_lemma_id": mt_id, "lemma_key": lemma_key}
    elif step.name == "external_sources":
        for row in _objects(parent.get("dialects")):
            key = _positive_decimal(row.get("dialect_id"))
            if key == "6":
                return {"dialect_id": key}
    elif step.name == "external_citation_records":
        # Source membership alone does not establish a positive citation result.
        # Current CAL returned an explicit empty state for 1CorH (issue #345);
        # this exact EbPar navigation yielded 26 rows in the bounded live probe.
        if parent.get("dialect_id") != "6":
            return None
        matches = [
            row for row in _objects(parent.get("sources")) if row.get("abbreviation") == "EbPar"
        ]
        canonical = "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar"
        if matches and all(row.get("citations_url") == canonical for row in matches):
            return {"source_abbrev": "EbPar"}
    elif step.name == "syriac_group":
        for row in _objects(parent.get("items")):
            key = _positive_decimal(row.get("upstream_id"))
            if key == "60420" and row.get("navigation_kind") == "group":
                return {"group_id": key}
    return None


def _positive_payload(step: FollowupStep, payload: dict[str, object]) -> bool:
    if step.name == "text_comments" and payload.get("status") != "found":
        return False
    contents = payload.get(step.positive_field)
    if step.positive_field == "entry":
        return isinstance(contents, dict) and bool(contents)
    if step.positive_field == "page":
        return isinstance(contents, dict) and bool(_objects(contents.get("lines")))
    return (
        isinstance(contents, list)
        and bool(contents)
        and all(
            (isinstance(row, dict) and bool(row)) or (isinstance(row, str) and bool(row.strip()))
            for row in contents
        )
    )


def complete_batch(outcomes: tuple[SmokeOutcome, ...], attempts: int) -> bool:
    names = tuple(step.name for step in STEPS)
    return (
        len(STEPS) == 21
        and len(set(names)) == len(names)
        and len({step.tool for step in STEPS if step.tool in TARGET_TOOLS}) == 12
        and all(step.tool in CURRENT_PUBLIC_TOOLS for step in STEPS)
        and tuple(outcome.case for outcome in outcomes) == names
        and all(outcome.category == "ok" for outcome in outcomes)
        and type(attempts) is int
        and len(STEPS) <= attempts <= _MAX_ATTEMPTS
    )


def complete_remaining(outcomes: tuple[SmokeOutcome, ...], attempts: int) -> bool:
    """Require the entire reviewed 17-step subset; never waive the failed comment probe."""
    names = tuple(step.name for step in REMAINDER_STEPS)
    return (
        names == _REVIEWED_REMAINDER_NAMES
        and len(set(names)) == 17
        and REMAINDER_STEPS[0].parent is None
        and all(step.tool not in {"cal_text_line_comments"} for step in REMAINDER_STEPS)
        and tuple(outcome.case for outcome in outcomes) == names
        and all(outcome.category == "ok" for outcome in outcomes)
        and type(attempts) is int
        and 17 <= attempts <= _MAX_ATTEMPTS
    )


def complete_syriac(outcomes: tuple[SmokeOutcome, ...], attempts: int) -> bool:
    """Prove the final previously unattempted CAL group path, without hiding other failures."""
    names = tuple(step.name for step in SYRIAC_STEPS)
    return (
        names == ("syriac_category", "syriac_group")
        and SYRIAC_STEPS[0].parent is None
        and SYRIAC_STEPS[1].parent == "syriac_category"
        and SYRIAC_STEPS[1].tool == "cal_syriac_group"
        and tuple(outcome.case for outcome in outcomes) == names
        and all(outcome.category == "ok" for outcome in outcomes)
        and type(attempts) is int
        and attempts == 2
    )


def complete_external(outcomes: tuple[SmokeOutcome, ...], attempts: int) -> bool:
    """Require all three dependent current external-citation MCP calls."""
    names = tuple(step.name for step in EXTERNAL_STEPS)
    return (
        names == ("external_dialects", "external_sources", "external_citation_records")
        and EXTERNAL_STEPS[0].parent is None
        and EXTERNAL_STEPS[1].parent == "external_dialects"
        and EXTERNAL_STEPS[2].parent == "external_sources"
        and tuple(outcome.case for outcome in outcomes) == names
        and all(outcome.category == "ok" for outcome in outcomes)
        and type(attempts) is int
        and attempts == 3
    )


def safe_failure_reason(outcome: SmokeOutcome, result: CallToolResult) -> SmokeOutcome:
    """Expose only allowlisted MCP error codes after centralized envelope validation.

    No server-supplied message, source URL, HTML or original exception can appear.
    This only refines presentation; category and stop-on-error policy are unchanged.
    """
    if outcome.category != "unavailable" or not result.is_error:
        return outcome
    payload = result.structured_content
    if not isinstance(payload, dict):
        return outcome
    error = payload.get("error")
    if not isinstance(error, dict):
        return outcome
    kind = error.get("kind")
    if kind not in {"network", "upstream_http", "content", "response_too_large"}:
        return outcome
    message = f"CAL {kind}"
    if kind == "upstream_http":
        status = error.get("status_code")
        if type(status) is int and 100 <= status <= 599:
            message += f" HTTP {status}"
    return SmokeOutcome(outcome.case, outcome.category, message)


async def run_cases(
    client: Client,
    *,
    steps: tuple[FollowupStep, ...] = STEPS,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[SmokeOutcome, ...]:
    try:
        listed = (await client.list_tools()).tools
    except Exception:
        return (SmokeOutcome("preflight", "harness", "cannot inspect MCP registry"),)
    if not valid_registry(listed):
        return (SmokeOutcome("preflight", "harness", "invalid installed MCP registry"),)
    tools = {tool.name: tool for tool in listed}
    passed: dict[str, dict[str, object]] = {}
    outcomes: list[SmokeOutcome] = []
    last_cal_finished: float | None = None
    for step in steps:
        arguments = select_arguments(step, passed)
        if arguments is None:
            outcomes.append(SmokeOutcome(step.name, "drift", "missing trusted CAL selector"))
            break
        if last_cal_finished is not None:
            remaining = _INTERVAL_SECONDS - (clock() - last_cal_finished)
            if remaining > 0:
                await sleep(remaining)
        case = SmokeCase(
            step.name,
            step.tool,
            arguments,
            expected_statuses=step.expected_statuses,
        )
        try:
            result = await client.call_tool(step.tool, arguments=arguments)
        except Exception:
            outcomes.append(SmokeOutcome(step.name, "harness", "installed MCP call failed"))
            break
        finally:
            last_cal_finished = clock()
        outcome = safe_failure_reason(evaluate_tool_result(case, tools[step.tool], result), result)
        if outcome.category == "ok":
            payload = result.structured_content
            if not isinstance(payload, dict) or not _positive_payload(step, payload):
                outcome = SmokeOutcome(step.name, "drift", "missing expected CAL result content")
            else:
                passed[step.name] = payload
        outcomes.append(outcome)
        if terminal_backpressure(result) or outcome.category != "ok":
            break
    return tuple(outcomes)


async def _run_live(
    executable: str, *, steps: tuple[FollowupStep, ...] = STEPS
) -> tuple[tuple[SmokeOutcome, ...], int]:
    with TemporaryDirectory(prefix="cal-mcp-followup-smoke-") as directory:
        count_path = Path(directory) / "attempts.json"
        env = dict(os.environ)
        env["CAL_MCP_LIVE_SMOKE_MAX_ATTEMPTS"] = str(_MAX_ATTEMPTS)
        env["CAL_MCP_LIVE_SMOKE_REPORT_PATH"] = str(count_path)
        async with Client(StdioServerParameters(command=executable, env=env)) as client:
            results = await run_cases(client, steps=steps)
        return results, _read_actual_attempts(count_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded manual follow-up MCP acceptance")
    parser.add_argument("--executable", help="absolute installed cal-mcp executable")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--remaining-only", action="store_true", help="run only #340 unattempted suffix"
    )
    mode.add_argument("--syriac-only", action="store_true", help="run only the two Syriac steps")
    mode.add_argument(
        "--external-only", action="store_true", help="run only the three external citation steps"
    )
    args = parser.parse_args()
    executable = args.executable or shutil.which("cal-mcp")
    if not executable:
        print(json.dumps({"status": "failed", "category": "harness"}), file=sys.stderr)
        raise SystemExit(1)
    selected_steps = (
        EXTERNAL_STEPS
        if args.external_only
        else SYRIAC_STEPS
        if args.syriac_only
        else REMAINDER_STEPS
        if args.remaining_only
        else STEPS
    )
    try:
        outcomes, attempts = asyncio.run(_run_live(executable, steps=selected_steps))
    except Exception:
        print(json.dumps({"status": "failed", "category": "harness"}), file=sys.stderr)
        raise SystemExit(1) from None
    if args.external_only:
        passed = complete_external(outcomes, attempts)
    elif args.syriac_only:
        passed = complete_syriac(outcomes, attempts)
    elif args.remaining_only:
        passed = complete_remaining(outcomes, attempts)
    else:
        passed = complete_batch(outcomes, attempts)
    print(
        json.dumps(
            {
                "status": "passed" if passed else "failed",
                "batch": (
                    "external_3"
                    if args.external_only
                    else "syriac_2"
                    if args.syriac_only
                    else "remaining_17"
                    if args.remaining_only
                    else "full_21"
                ),
                "actual_cal_transport_attempts": attempts,
                "max_cal_transport_attempts": (
                    3 if args.external_only else 2 if args.syriac_only else _MAX_ATTEMPTS
                ),
                "cases": [asdict(outcome) for outcome in outcomes],
            },
            sort_keys=True,
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
