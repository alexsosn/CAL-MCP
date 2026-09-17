from __future__ import annotations

from pathlib import Path

from cal_mcp.release_surface import V01_PUBLIC_TOOLS

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COUNT = len(V01_PUBLIC_TOOLS)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_user_facing_v01_tool_count_claims_match_release_manifest() -> None:
    claims = {
        "README.md": (
            f"{EXPECTED_COUNT} public tools",
            f"{EXPECTED_COUNT}-tool surface",
        ),
        "docs/index.md": (f"contains {EXPECTED_COUNT} tools",),
        "docs/installation.md": (f"frozen {EXPECTED_COUNT}-tool MCP surface",),
        "docs/integrations/standalone-mcp.md": (f"surface contains {EXPECTED_COUNT} public tools",),
        "CHANGELOG.md": (
            f"freezes **{EXPECTED_COUNT} public tools**",
            f"frozen {EXPECTED_COUNT}-tool schema",
        ),
    }

    missing: list[str] = []
    for path, expected_phrases in claims.items():
        text = _read(path)
        for phrase in expected_phrases:
            if phrase not in text:
                missing.append(f"{path}: {phrase}")

    assert missing == []
