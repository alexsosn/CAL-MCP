"""Offline adversarial checks for the additional installed-wheel CAL acceptance batch."""

import importlib
from types import SimpleNamespace

from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS
from cal_mcp.stdio_live_smoke import DEFAULT_SMOKE_CASES, SmokeOutcome


def _batch():
    return importlib.import_module("cal_mcp.pre_release_smoke")


def test_batch_uses_distinct_uncovered_public_tools() -> None:
    batch = _batch()
    existing = {case.tool for case in DEFAULT_SMOKE_CASES}
    actual = [case.tool for case in batch.BATCH_CASES]
    assert len(actual) == len(set(actual)) == 13
    assert set(actual) <= CURRENT_PUBLIC_TOOLS - existing
    assert {case.name for case in batch.BATCH_CASES} == set(batch.REQUIRED_CONTENT_FIELDS)
    assert all(case.from_case is None for case in batch.BATCH_CASES)


def test_success_requires_every_reviewed_case_and_actual_transport() -> None:
    batch = _batch()
    passed = tuple(SmokeOutcome(case.name, "ok", "success") for case in batch.BATCH_CASES)
    assert batch.complete_batch(passed, 13)
    assert batch.complete_batch(passed, 25)
    assert not batch.complete_batch(passed, 12)
    assert not batch.complete_batch(passed, 26)
    assert not batch.complete_batch(passed[:-1], 13)
    assert not batch.complete_batch(passed + passed[-1:], 14)
    assert not batch.complete_batch(
        passed[:-1] + (SmokeOutcome(passed[-1].case, "drift", "empty result"),), 13
    )
    assert not batch.complete_batch(
        passed[:-1] + (SmokeOutcome(passed[-1].case, "skipped_dependency", "missing"),), 13
    )


def test_nonempty_result_checks_reject_vacuous_schema_valid_success() -> None:
    batch = _batch()
    for case in batch.BATCH_CASES:
        key = batch.REQUIRED_CONTENT_FIELDS[case.name]
        assert not batch.valid_content(case, {})
        assert not batch.valid_content(case, {key: []})
        assert not batch.valid_content(case, {key: [None]})
        assert batch.valid_content(case, {key: [{"value": "fixture"}], "status": "found"})


def test_empty_analyses_are_not_passing_token_success() -> None:
    batch = _batch()
    case = next(case for case in batch.BATCH_CASES if case.tool == "cal_token_analysis")
    assert not batch.valid_content(case, {"status": "not_found", "candidates": []})
    assert not batch.valid_content(case, {"status": "found", "candidates": []})
    assert batch.valid_content(case, {"status": "found", "candidates": [{"lemma_key": "br N"}]})


def test_suite_cannot_accept_duplicate_registry_or_missing_output_schemas() -> None:
    batch = _batch()
    listed = [
        SimpleNamespace(name=name, output_schema={"type": "object"})
        for name in CURRENT_PUBLIC_TOOLS
    ]
    assert batch.valid_registry(listed)
    assert not batch.valid_registry(listed[:-1])
    assert not batch.valid_registry(listed + listed[-1:])
    broken = [SimpleNamespace(name=x.name, output_schema=x.output_schema) for x in listed]
    broken[0].output_schema = None
    assert not batch.valid_registry(broken)


def test_terminal_backpressure_never_allows_further_calls() -> None:
    batch = _batch()
    assert batch.terminal_backpressure(
        SimpleNamespace(
            is_error=True,
            structured_content={"error": {"kind": "upstream_http", "status_code": 429}},
        )
    )
    assert batch.terminal_backpressure(
        SimpleNamespace(
            is_error=True, structured_content={"error": {"kind": "local_rate_limit"}}
        )
    )
    assert not batch.terminal_backpressure(
        SimpleNamespace(
            is_error=True,
            structured_content={"error": {"kind": "upstream_http", "status_code": 503}},
        )
    )
