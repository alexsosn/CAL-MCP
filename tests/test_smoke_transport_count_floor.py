"""Release smoke needs plausible counted CAL I/O for all 11 scholarly cases (#305).

All CLI executions stub the installed process: no live requests or subprocesses.
"""

from __future__ import annotations

import json

import pytest

import cal_mcp.stdio_live_smoke as smoke
from cal_mcp.stdio_live_smoke import SmokeOutcome


def _full_success() -> tuple[SmokeOutcome, ...]:
    return tuple(SmokeOutcome(case.name, "ok", "success") for case in smoke.DEFAULT_SMOKE_CASES)


def _run_stubbed_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcomes: tuple[SmokeOutcome, ...],
    attempts: int,
    *,
    expect_exit: bool,
) -> dict[str, object]:
    async def fake_run(executable: str) -> tuple[tuple[SmokeOutcome, ...], int]:
        assert executable == "/offline/cal-mcp"
        return outcomes, attempts

    monkeypatch.setattr(smoke, "_run_live", fake_run)
    monkeypatch.setattr("sys.argv", ["live-smoke", "--executable", "/offline/cal-mcp"])
    if expect_exit:
        with pytest.raises(SystemExit) as exit_info:
            smoke.main()
        assert exit_info.value.code == 1
    else:
        smoke.main()
    report = json.loads(capsys.readouterr().out)
    assert isinstance(report, dict)
    return report


@pytest.mark.parametrize("attempts", [1, 2, 8, 10])
def test_full_report_below_eleven_live_transports_cannot_authorize_publication(
    attempts: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    outcomes = _full_success()
    assert len(outcomes) == 12
    report = _run_stubbed_cli(monkeypatch, capsys, outcomes, attempts, expect_exit=True)
    assert report["status"] == "failed"
    assert report["category"] == "harness"
    assert report["reason"] == "incomplete_smoke_acceptance"
    assert report["actual_cal_transport_attempts"] == attempts
    assert len(report["cases"]) == 12
    assert all(case["category"] == "ok" for case in report["cases"])


@pytest.mark.parametrize("attempts", [11, 25])
def test_full_report_with_at_least_eleven_measured_starts_remains_eligible(
    attempts: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _run_stubbed_cli(
        monkeypatch, capsys, _full_success(), attempts, expect_exit=False
    )
    assert report["status"] == "passed"
    assert report["actual_cal_transport_attempts"] == attempts
    assert len(report["cases"]) == 12


def test_terminal_upstream_failure_keeps_its_original_category_below_floor(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    names = tuple(case.name for case in smoke.DEFAULT_SMOKE_CASES)
    outcomes = (
        SmokeOutcome(names[0], "ok", "success"),
        SmokeOutcome(names[1], "unavailable", "CAL upstream unavailable or unsafe"),
    )
    report = _run_stubbed_cli(monkeypatch, capsys, outcomes, 1, expect_exit=True)
    assert report["status"] == "failed"
    assert report["cases"][1]["category"] == "unavailable"
    assert report.get("reason") != "incomplete_smoke_acceptance"
    assert report["actual_cal_transport_attempts"] == 1
