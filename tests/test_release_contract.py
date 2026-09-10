from __future__ import annotations

import asyncio
import importlib
import json
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
from cal_mcp.release_surface import V01_PUBLIC_TOOLS

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
INSTALLATION_DOC = ROOT / "docs" / "installation.md"
STANDALONE_DOC = ROOT / "docs" / "integrations" / "standalone-mcp.md"
TESTING_GUIDE = ROOT / "wiki" / "testing.md"
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
    assert "31 public tools" in changelog
    assert "31-tool schema" in changelog
    assert "cal_kwic_full_context" in changelog
    assert "cal_syriac_group" in changelog
    assert "#39" in changelog

    assert LIVE_SMOKE_WORKFLOW.exists()
    assert RELEASE_WORKFLOW.exists()
    assert RELEASE_VERIFY_SCRIPT.exists()


def test_v01_release_coordinates_are_documented_without_stale_dev_version() -> None:
    installation = INSTALLATION_DOC.read_text(encoding="utf-8")
    standalone = STANDALONE_DOC.read_text(encoding="utf-8")

    assert "0.1.0.dev0" not in installation
    assert "0.1.0.dev0" not in standalone
    assert "cal-mcp==0.1.0" in installation
    assert "cal-mcp==0.1.0" in standalone
    assert "command: cal-mcp" in standalone
    assert "transport: stdio" in standalone


def test_live_smoke_operator_documentation_freezes_invocation_and_budget() -> None:
    testing = TESTING_GUIDE.read_text(encoding="utf-8")

    assert ".github/workflows/live-smoke.yml" in testing
    assert "python -m cal_mcp.live_smoke" in testing
    assert "9" in testing
    assert "concurrency" in testing.lower()
    assert "retries" in testing.lower()
    assert "cache" in testing.lower()


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
    assert "V01_PUBLIC_TOOLS" in verifier
    assert len(V01_PUBLIC_TOOLS) == 31


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


@pytest.mark.anyio
async def test_live_smoke_failure_records_consumed_request_count() -> None:
    module = _live_smoke_module()

    async def transport(request: CalRequest, config: object) -> CalResponse:
        del request, config
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/test",
            body=b"ok",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 7, tzinfo=UTC),
        )

    async def consume_then_fail(client: object) -> None:
        typed_client = client
        await typed_client.fetch(
            CalRequest(method="GET", path="test"),
            parser=lambda response: response.body,
            cache_namespace="release-failure-count-test",
        )
        raise ConcordanceParseError("changed markup after one request")

    client = module.BudgetCalHttpClient(transport=transport)
    case = module.SmokeCase(name="synthetic_after_request", operation=consume_then_fail)
    try:
        with pytest.raises(module.LiveSmokeFailure) as exc_info:
            await module.run_live_smoke(cases=(case,), client=client)
        assert exc_info.value.request_count == 1
        assert client.request_count == 1
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "interruption_type",
    [KeyboardInterrupt, SystemExit, asyncio.CancelledError],
)
@pytest.mark.anyio
async def test_live_smoke_runner_preserves_process_interruptions(
    interruption_type: type[BaseException],
) -> None:
    module = _live_smoke_module()

    async def interrupt(client: object) -> None:
        del client
        raise interruption_type()

    client = module.BudgetCalHttpClient(
        transport=lambda request, config: pytest.fail("transport must not be reached")
    )
    case = module.SmokeCase(name="synthetic_interrupt", operation=interrupt)
    try:
        with pytest.raises(interruption_type):
            await module.run_live_smoke(cases=(case,), client=client)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_live_smoke_budget_failure_records_nine_consumed_requests() -> None:
    module = _live_smoke_module()
    upstream_calls = 0

    async def transport(request: CalRequest, config: object) -> CalResponse:
        nonlocal upstream_calls
        del request, config
        upstream_calls += 1
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/test",
            body=b"ok",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 7, tzinfo=UTC),
        )

    async def exhaust_budget(client: object) -> None:
        typed_client = client
        for index in range(module.MAX_CAL_REQUESTS + 1):
            await typed_client.fetch(
                CalRequest(method="GET", path="test", params=(("n", str(index)),)),
                parser=lambda response: response.body,
                cache_namespace="release-budget-failure-test",
            )

    client = module.BudgetCalHttpClient(transport=transport)
    case = module.SmokeCase(name="synthetic_budget", operation=exhaust_budget)
    try:
        with pytest.raises(module.LiveSmokeFailure) as exc_info:
            await module.run_live_smoke(cases=(case,), client=client)
        assert isinstance(exc_info.value.cause, module.LiveSmokeBudgetExceeded)
        assert exc_info.value.request_count == module.MAX_CAL_REQUESTS
        assert upstream_calls == module.MAX_CAL_REQUESTS
    finally:
        await client.aclose()


def test_live_smoke_cli_reports_expected_failure_as_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _live_smoke_module()
    failure = module.LiveSmokeFailure(
        "synthetic_drift",
        "drift",
        ConcordanceParseError("changed markup"),
    )

    async def fail_async_main() -> None:
        raise failure

    monkeypatch.setattr(module, "_async_main", fail_async_main)

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "case": "synthetic_drift",
        "category": "drift",
        "cause": "changed markup",
        "max_cal_requests": module.MAX_CAL_REQUESTS,
        "request_count": 0,
        "status": "failed",
    }


def test_live_smoke_cli_does_not_hide_unrelated_harness_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _live_smoke_module()

    async def fail_async_main() -> None:
        raise ValueError("unexpected harness bug")

    monkeypatch.setattr(module, "_async_main", fail_async_main)

    with pytest.raises(ValueError, match="unexpected harness bug"):
        module.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
