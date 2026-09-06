from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_v0_1_release_metadata_and_docs_are_finalized() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["name"] == "cal-mcp"
    assert pyproject["project"]["version"] == "0.1.0"
    assert pyproject["project"]["scripts"] == {"cal-mcp": "cal_mcp.server:main"}

    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert "## 0.1.0 — 2026-09-06" in changelog
    assert "26 public tools" in changelog
    assert "cal-mcp" in changelog
    assert "stdio" in changelog.lower()

    installation = (ROOT / "docs" / "installation.md").read_text()
    standalone = (ROOT / "docs" / "integrations" / "standalone-mcp.md").read_text()
    assert "0.1.0.dev0" not in installation
    assert "pre-release" not in installation.lower()
    assert "No stable published v0.1 package" not in standalone
    assert "cal-mcp" in standalone
    assert "transport: stdio" in standalone
