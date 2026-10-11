"""Issue #303: the installed-wheel release gate must never pass an incomplete smoke matrix.

These tests stub the complete installed-stdio runner. No CAL network or subprocess is used.
"""

from __future__ import annotations

import json

import pytest

import cal_mcp.stdio_live_smoke as smoke
from cal_mcp.stdio_live_smoke import SmokeOutcome


def _outcomes(names: tuple[str, ...]) -> tuple[SmokeOutcome, ...]:
    return tuple(SmokeOutcome(name, "ok", "success") for name in names)


def _invoke_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcomes: tuple[SmokeOutcome, ...],
    attempts: int,
) -> dict[str, object]:
    async def stub_runner(executable: str) -> tuple[tuple[SmokeOutcome, ...], int]:
        assert executable == "/offline/bin/cal-mcp"
        return outcomes, attempts

    monkeypatch.setattr(smoke, "_run_live", stub_runner)
    monkeypatch.setattr(
        "sys.argv", ["stdio-live-smoke", "--executable", "/offline/bin/cal-mcp"]
    )
    with pytest.raises(SystemExit) as exit_info:
        smoke.main()
    assert exit_info.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert isinstance(output, dict)
    return output


@pytest.mark.parametrize(
    "case",
    ["empty", "prefix", "reordered", "duplicate", "unknown", "zero_attempts"],
)
def test_incomplete_or_forged_smoke_matrix_fails_release_closed(
    case: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    names = tuple(item.name for item in smoke.DEFAULT_SMOKE_CASES)
    assert len(names) == 12
    if case == "empty":
        outcomes = ()
    elif case == "prefix":
        outcomes = _outcomes(names[:3])
    elif case == "reordered":
        outcomes = _outcomes((names[1], names[0], *names[2:]))
    elif case == "duplicate":
        outcomes = _outcomes((*names[:-1], names[-2]))
    elif case == "unknown":
        outcomes = _outcomes((*names[:-1], "invented_tool"))
    else:
        outcomes = _outcomes(names)
    attempts = 0 if case == "zero_attempts" else 2
    report = _invoke_cli(monkeypatch, capsys, outcomes, attempts)
    assert report["status"] == "failed"
    assert report["category"] == "harness"
    assert report["reason"] == "incomplete_smoke_acceptance"
    assert report["actual_cal_transport_attempts"] == attempts
    assert report["cases"] == [
        {"case": o.case, "category": o.category, "message": o.message}
        for o in outcomes
    ]


@pytest.mark.parametrize("case", ["empty_expected", "short_expected", "duplicate_expected"])
def test_release_gate_rejects_a_mutated_required_matrix(
    case: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    names = tuple(smoke.DEFAULT_SMOKE_CASES)
    if case == "empty_expected":
        required = ()
    elif case == "short_expected":
        required = names[:1]
    else:
        required = (*names[:-1], names[-2])
    monkeypatch.setattr(smoke, "DEFAULT_SMOKE_CASES", required)
    report = _invoke_cli(
        monkeypatch,
        capsys,
        _outcomes(tuple(item.name for item in required)),
        attempts=3,
    )
    assert report["status"] == "failed"
    assert report["category"] == "harness"


def test_full_ordered_twelve_case_positive_count_can_pass(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    outcomes = _outcomes(tuple(item.name for item in smoke.DEFAULT_SMOKE_CASES))

    async def stub_runner(executable: str) -> tuple[tuple[SmokeOutcome, ...], int]:
        assert executable == "/offline/bin/cal-mcp"
        return outcomes, 11

    monkeypatch.setattr(smoke, "_run_live", stub_runner)
    monkeypatch.setattr(
        "sys.argv", ["stdio-live-smoke", "--executable", "/offline/bin/cal-mcp"]
    )
    smoke.main()
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "passed"
    assert report["actual_cal_transport_attempts"] == 11
    assert len(report["cases"]) == 12


def test_genuine_terminal_rate_limit_is_still_failing_and_unmasked(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    names = tuple(item.name for item in smoke.DEFAULT_SMOKE_CASES)
    outcomes = (
        SmokeOutcome(names[0], "ok", "success"),
        SmokeOutcome(names[1], "unavailable", "CAL upstream unavailable or unsafe"),
    )
    report = _invoke_cli(monkeypatch, capsys, outcomes, attempts=1)
    assert report["status"] == "failed"
    assert report["cases"][1]["category"] == "unavailable"
