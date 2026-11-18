"""Tag publishing gates all 37 routes; manual drift smoke remains representative."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github" / "workflows" / "release.yml"
WEEKLY = ROOT / ".github" / "workflows" / "live-smoke.yml"


def _release_smoke_job() -> str:
    workflow = RELEASE.read_text(encoding="utf-8")
    return workflow.split("\n  live-smoke:\n", 1)[1].split("\n  publish-pypi:\n", 1)[0]


def test_release_smoke_installs_exact_uploaded_wheel_not_source() -> None:
    workflow = RELEASE.read_text(encoding="utf-8")
    job = _release_smoke_job()
    assert "needs: build-and-test" in job
    assert "group: cal-mcp-live-smoke" in job
    assert "cancel-in-progress: false" in job
    assert "actions/download-artifact@v5" in job
    assert "name: python-distributions" in job
    assert "dist/*.whl" in job
    assert "-m cal_mcp.stdio_live_smoke" in job
    assert "actions/checkout@" not in job
    assert "pip install ." not in job
    assert "cal_mcp.live_smoke" not in job
    assert "continue-on-error" not in job

    # Trusted publication remains after, and depends upon, the E2E job.
    publish = workflow.split("\n  publish-pypi:\n", 1)[1]
    assert "- live-smoke" in publish
    assert "pypa/gh-action-pypi-publish@release/v1" in publish


def test_scheduled_smoke_uses_one_installed_wheel_suite_without_source_shadowing() -> None:
    workflow = WEEKLY.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "group: cal-mcp-live-smoke" in workflow
    assert "schedule:" not in workflow
    assert "python -m build --wheel" in workflow
    assert "dist/*.whl" in workflow
    assert 'cd "$RUNNER_TEMP"' in workflow
    assert "-m cal_mcp.stdio_live_smoke" in workflow
    assert "-m cal_mcp.live_smoke" not in workflow
    assert "continue-on-error" not in workflow
    assert "pull_request:" not in workflow


def test_tag_uses_three_fixed_wheel_suites_but_manual_smoke_stays_one() -> None:
    release = RELEASE.read_text(encoding="utf-8")
    weekly = WEEKLY.read_text(encoding="utf-8")
    job = _release_smoke_job()
    suites = (
        "cal_mcp.pre_release_followup_smoke",
        "cal_mcp.pre_release_smoke",
        "cal_mcp.stdio_live_smoke",
    )
    assert job.count("-m cal_mcp.stdio_live_smoke") == 1
    assert all(job.count(f"-m {suite}") == 1 for suite in suites)
    assert job.index(suites[0]) < job.index(suites[1]) < job.index(suites[2])
    assert job.count("sleep 60") >= 2
    assert "actions/checkout@" not in job
    assert all(suite not in weekly for suite in suites[:-1])
    assert weekly.count("cal_mcp.stdio_live_smoke") == 1
    assert "cal_mcp.live_smoke" not in release + weekly


def test_both_smoke_workflow_jobs_allow_bounded_inter_case_wait() -> None:
    assert "timeout-minutes: 90" in _release_smoke_job()
    weekly = WEEKLY.read_text(encoding="utf-8")
    job = weekly.split("  live-smoke:", 1)[1]
    assert "timeout-minutes: 30" in job
    # No automatic live CAL probing while the observed 429 release gate is open.
    assert "workflow_dispatch:" in weekly
    assert "schedule:" not in weekly
