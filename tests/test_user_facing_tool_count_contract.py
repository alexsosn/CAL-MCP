"""Keep historical published and new release-candidate tool counts version-scoped."""

from __future__ import annotations

import re
from pathlib import Path

from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS, V01_PUBLIC_TOOLS

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_user_facing_versioned_tool_counts_match_both_manifests() -> None:
    assert len(V01_PUBLIC_TOOLS) == 36
    assert len(CURRENT_PUBLIC_TOOLS) == 37
    assert CURRENT_PUBLIC_TOOLS - V01_PUBLIC_TOOLS == {"cal_bibliography_recent"}

    for path in (
        "README.md",
        "docs/index.md",
        "docs/installation.md",
        "docs/integrations/standalone-mcp.md",
    ):
        content = _read(path)
        # Each count must refer to its version, not an unrelated nearby number.
        assert re.search(r"v?0\.1\.0[\s\S]{0,160}\b36\b", content, re.IGNORECASE), path
        assert re.search(r"v?0\.2\.0[\s\S]{0,180}\b37(?:th)?\b", content, re.IGNORECASE), path

    changelog = _read("CHANGELOG.md")
    assert "## 0.1.0" in changelog
    historical = changelog.split("## 0.1.0", 1)[1]
    assert "v0.1.0 freezes **36 public tools**" in historical
    candidate = changelog.split("## 0.2.0", 1)[1].split("## 0.1.0", 1)[0]
    assert "37/37 tools" in candidate
    assert "47/47 scenarios" in candidate
