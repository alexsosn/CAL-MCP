"""Offline contract tests for the released CAL-MCP → Agora handoff (#16)."""

from __future__ import annotations

import tomllib
from pathlib import Path

from cal_mcp.stdio_live_smoke import DEFAULT_SMOKE_CASES

ROOT = Path(__file__).resolve().parents[1]
AGORA_DOC = ROOT / "docs" / "integrations" / "agora.md"


def test_agora_handoff_matches_exact_published_package_metadata() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["name"] == "cal-mcp"
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["requires-python"] == ">=3.11"
    assert project["project"]["scripts"]["cal-mcp"] == "cal_mcp.server:main"

    doc = AGORA_DOC.read_text(encoding="utf-8")
    for exact in (
        "cal-mcp==0.1.0",
        "cal-mcp",
        "stdio",
        "Python 3.11",
        "36 public tools",
        "https://cal.huc.edu/",
        "upstream-dependent",
        "Agora#222",
        "not a hosted",
    ):
        assert exact in doc


def test_agora_handoff_one_call_smoke_is_existing_fixed_release_case() -> None:
    case = next(case for case in DEFAULT_SMOKE_CASES if case.name == "lexicon_noun")
    assert case.tool == "cal_lexicon_lookup"
    assert case.arguments == {"query": "br", "lemma_key": "br N"}
    assert case.expected_statuses == ("found",)

    doc = AGORA_DOC.read_text(encoding="utf-8")
    assert "cal_lexicon_lookup" in doc
    assert '"query": "br"' in doc
    assert '"lemma_key": "br N"' in doc
    assert "one" in doc.lower()
    assert "without contacting CAL" in doc
    assert "3 seconds" in doc
    assert "8 starts" in doc
    assert "60-second" in doc


def test_released_user_documentation_no_longer_calls_v010_prerelease() -> None:
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    installation = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
    assert "**Status:** released v0.1.0" in index
    assert "pre-release" not in index.lower()
    assert "https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0" in index
    assert "https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0" in installation
    assert "manual-only" in installation
