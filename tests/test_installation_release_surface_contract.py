"""Documentation regression: standalone install surface must match release manifest."""

from __future__ import annotations

import re
from pathlib import Path

from cal_mcp.release_surface import V01_PUBLIC_TOOLS

ROOT = Path(__file__).resolve().parents[1]


def test_installation_guide_tool_count_matches_authoritative_release_surface() -> None:
    text = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
    described_counts = re.findall(r"\b(\d+)-tool MCP surface\b", text)

    assert len(described_counts) == 1, (
        "Expected exactly one release surface count in installation guide"
    )
    assert int(described_counts[0]) == len(V01_PUBLIC_TOOLS)
