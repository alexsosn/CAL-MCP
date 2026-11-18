"""Prepublication contract for the reviewed v0.2.0 researcher release candidate.

Pure local inspection: no CAL requests, no PyPI publication, no git tagging.
"""

import tomllib
from pathlib import Path

from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS, V01_PUBLIC_TOOLS

ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"


def test_stable_candidate_version_without_mutating_historical_v01_contract() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "cal-mcp"
    assert project["readme"] == "README.md"
    assert project["version"] == "0.2.0"
    assert len(V01_PUBLIC_TOOLS) == 36
    assert len(CURRENT_PUBLIC_TOOLS) == 37
    assert V01_PUBLIC_TOOLS <= CURRENT_PUBLIC_TOOLS
    assert {"cal_bibliography_recent"} == CURRENT_PUBLIC_TOOLS - V01_PUBLIC_TOOLS


def test_documentation_names_stable_unpublished_candidate_and_historical_pin() -> None:
    current_documents = (
        "README.md",
        "CHANGELOG.md",
        "docs/index.md",
        "docs/installation.md",
        "docs/getting-started.md",
        "docs/limitations.md",
        "docs/tools/bibliography.md",
    )
    for path in current_documents:
        content = (ROOT / path).read_text(encoding="utf-8")
        assert "0.2.0" in content, path
        assert "release candidate" in content.lower(), path
        assert "0.2.0.dev0" not in content, path
        assert "0.1.0" in content, path
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    installation = (ROOT / "docs/installation.md").read_text(encoding="utf-8")
    assert "not yet published" not in readme.lower()
    assert "pypi.org/project/cal-mcp/" in readme
    assert "36" in readme and "37" in readme
    assert "not yet published" not in installation.lower()
    assert 'pip install "cal-mcp==0.1.0"' in installation
    assert 'pip install "cal-mcp==0.2.0"' not in installation


def test_release_tag_pipeline_checks_full_37_47_same_artifact_before_pypi() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert '    tags:\n      - "v*"' in workflow
    assert "timeout-minutes: 90" in workflow
    assert "Full 37-tool" in workflow
    assert "len(CURRENT_PUBLIC_TOOLS) == 37" in workflow
    assert "len(names) == len(set(names)) == 47" in workflow
    assert "base | extra | dependent == CURRENT_PUBLIC_TOOLS" in workflow
    assert "cal_mcp.pre_release_followup_smoke" in workflow
    assert "cal_mcp.pre_release_smoke" in workflow
    assert "cal_mcp.stdio_live_smoke" in workflow
    assert (
        workflow.index("-m cal_mcp.pre_release_followup_smoke")
        < workflow.index("-m cal_mcp.pre_release_smoke")
        < workflow.index("-m cal_mcp.stdio_live_smoke")
    )
    assert workflow.count("sleep 60") >= 2
    assert "name: publish-pypi" not in workflow
    assert "  publish-pypi:\n    needs:\n      - build-and-test\n      - live-smoke" in workflow
    assert "    environment: pypi" in workflow
    assert 'python scripts/verify_release_artifact.py dist --tag "${GITHUB_REF_NAME}"' in workflow
