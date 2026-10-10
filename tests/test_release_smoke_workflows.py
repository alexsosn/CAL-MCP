"""Issue #157: release must gate publishing on exactly one installed-wheel MCP smoke."""

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
    assert "schedule:" in workflow
    assert "python -m build --wheel" in workflow
    assert "dist/*.whl" in workflow
    assert 'cd "$RUNNER_TEMP"' in workflow
    assert "-m cal_mcp.stdio_live_smoke" in workflow
    assert "-m cal_mcp.live_smoke" not in workflow
    assert "continue-on-error" not in workflow
    assert "pull_request:" not in workflow


def test_no_old_and_new_live_suites_are_stacked_in_one_workflow() -> None:
    for path in (RELEASE, WEEKLY):
        workflow = path.read_text(encoding="utf-8")
        assert workflow.count("cal_mcp.stdio_live_smoke") == 1, path
        assert "cal_mcp.live_smoke" not in workflow, path
