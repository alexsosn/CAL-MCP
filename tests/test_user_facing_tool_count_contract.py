from __future__ import annotations

import re
from pathlib import Path

from cal_mcp.release_surface import V01_PUBLIC_TOOLS

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COUNT = len(V01_PUBLIC_TOOLS)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_user_facing_v01_tool_count_claims_match_release_manifest() -> None:
    claims = {
        "README.md": (
            r"\b(\d+) public tools\b",
            r"\b(\d+)-tool surface\b",
        ),
        "docs/index.md": (r"\bcontains (\d+) tools\b",),
        "docs/installation.md": (r"\bfrozen (\d+)-tool MCP surface\b",),
        "docs/integrations/standalone-mcp.md": (r"\bsurface contains (\d+) public tools\b",),
        "CHANGELOG.md": (
            r"freezes \*\*(\d+) public tools\*\*",
            r"\bfrozen (\d+)-tool schema\b",
        ),
    }

    mismatches: list[str] = []
    for path, patterns in claims.items():
        text = _read(path)
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches != [str(EXPECTED_COUNT)]:
                mismatches.append(f"{path}: {pattern} -> {matches!r}")

    assert mismatches == []
