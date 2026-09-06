from __future__ import annotations

import importlib
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

from cal_mcp.client import (
    CalContentError,
    CalNetworkError,
    CalRequest,
    CalResponse,
    CalUpstreamError,
)
from cal_mcp.concordance import ConcordanceParseError

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
LIVE_SMOKE_WORKFLOW = ROOT / ".github" / "workflows" / "live-smoke.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
RELEASE_VERIFY_SCRIPT = ROOT / "scripts" / "verify_release_artifact.py"


def _live_smoke_module() -> ModuleType:
    try:
        return importlib.import_module("cal_mcp.live_smoke")
    except ModuleNotFoundError:
        pytest.skip("cal_mcp.live_smoke absence is covered by the release-file contract")


def test_v01_release_metadata_and_artifacts_are_declared() -> None:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]

    assert project["name"] == "cal-mcp"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.11"
    assert project["scripts"]["cal-mcp"] == "cal_mcp.server:main"

    assert CHANGELOG.exists()
    changelog = CHANGELOG.read_text(encoding="utf-8")
    assert "0.1.0" in changelog
    assert "26" in changelog
    assert "#39" in changelog

    assert LIVE_SMOKE_WORKFLOW.exists()
    assert RELEASE_WORKFLOW.exists()
    assert RELEASE_VERIFY_SCRIPT.exists()


def test_live_smoke_workflow_is_separate_and_bounded() -> None:
    assert LIVE_SMOKE_WORKFLOW.exists()
    workflow = LIVE_SMOKE_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "live_smoke" in workflow
    assert "pull_request:" not in workflow


def test_release_workflow_uses_least_privilege_trusted_publishing() -> None:
    assert RELEASE_WORKFLOW.exists()
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "tags:" in workflow
    assert "v*" in workflow
    assert "environment: pypi" in workflow
    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "verify_release_artifact.py" in workflow
    assert "live_smoke" in workflow
    assert "PYPI_TOKEN" not in workflow
    assert "password:" not in workflow


def test_release_verifier_checks_tag_version_and_clean_wheel_install() -> None:
    assert RELEASE_VERIFY_SCRIPT.exists()
    verifier = RELEASE_VERIFY_SCRIPT.read_text(encoding="utf-8")

    assert "0.1.0" not in verifier
    assert "venv" in verifier
    assert "cal-mcp" in verifier
    assert "StdioServerParameters" in verifier
    assert "26" in verifier


def test_live_smoke_constants_and_default_cases_are_frozen() -> None:
    module = _live_smoke_module()

    assert module.MAX_CAL_REQUESTS == 9
    assert len(module.DEFAULT_SMOKE_CASES) == 8
    assert [case.name for case in module.DEFAULT_SMOKE_CASES] == [
        "lexicon",
        "text_search",
        "text_concordance",
        "bibliography",
        "dictionary_collation",
        "external_citations",
        "targum",
        "syriac",
    ]


def test_live_smoke_failure_classification_is_diagnostic() -> None:
    module = _live_smoke_module()

    assert module.classify_smoke_exception(ConcordanceParseError("drift")) == "drift"
    assert module.classify_smoke_exception(CalNetworkError("offline")) == "upstream"
    assert (
        module.classify_smoke_exception(CalUpstreamError(503, "https://cal.huc.edu/test"))
        == "upstream"
    )
    assert module.classify_smoke_exception(CalContentError("maintenance")) == "content"
    assert module.classify_smoke_exception(ValueError("harness")) == "harness"


@pytest.mark.anyio
async def test_live_smoke_client_enforces_request_budget_and_safe_config() -> None:
    module = _live_smoke_module()

    async def transport(request: CalRequest, config: object) -> CalResponse:
        del request, config
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/test",
            body=b"ok",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 6, tzinfo=UTC),
        )

    client = module.BudgetCalHttpClient(transport=transport)
    assert client.config.max_concurrency == 1
    assert client.config.max_retries == 0
    assert client.config.cache_enabled is False

    try:
        for index in range(module.MAX_CAL_REQUESTS):
            result = await client.fetch(
                CalRequest(method="GET", path="test", params=(("n", str(index)),)),
                parser=lambda response: response.body,
                cache_namespace="release-budget-test",
            )
            assert result.value == b"ok"

        with pytest.raises(module.LiveSmokeBudgetExceeded):
            await client.fetch(
                CalRequest(method="GET", path="test", params=(("n", "overflow"),)),
                parser=lambda response: response.body,
                cache_namespace="release-budget-test",
            )
        assert client.request_count == module.MAX_CAL_REQUESTS
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_live_smoke_runner_turns_case_failure_into_non_success() -> None:
    module = _live_smoke_module()

    async def transport(request: CalRequest, config: object) -> CalResponse:
        del request, config
        raise AssertionError("this test must not reach transport")

    async def fail_with_drift(client: object) -> None:
        del client
        raise ConcordanceParseError("changed markup")

    client = module.BudgetCalHttpClient(transport=transport)
    case = module.SmokeCase(name="synthetic_drift", operation=fail_with_drift)
    try:
        with pytest.raises(module.LiveSmokeFailure) as exc_info:
            await module.run_live_smoke(cases=(case,), client=client)
        assert exc_info.value.case_name == "synthetic_drift"
        assert exc_info.value.category == "drift"
        assert client.request_count == 0
    finally:
        await client.aclose()
