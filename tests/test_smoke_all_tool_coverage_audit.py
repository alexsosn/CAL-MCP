"""Source-grounded disclosure of real installed-wheel live smoke scope (no CAL I/O)."""

from pathlib import Path

from cal_mcp.release_surface import CURRENT_PUBLIC_TOOLS
from cal_mcp.stdio_live_smoke import DEFAULT_SMOKE_CASES

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/research/issue-338-coverage.md"


def test_current_live_smoke_is_not_all_tool_verification() -> None:
    tool_names = {case.tool for case in DEFAULT_SMOKE_CASES}
    assert len(DEFAULT_SMOKE_CASES) == 13
    assert len(CURRENT_PUBLIC_TOOLS) == 37
    assert len(tool_names) == 12
    assert tool_names <= CURRENT_PUBLIC_TOOLS
    assert len(CURRENT_PUBLIC_TOOLS - tool_names) == 25
    assert sum(case.tool == "cal_convert_to_code" for case in DEFAULT_SMOKE_CASES) == 1
    assert len({case.name for case in DEFAULT_SMOKE_CASES}) == len(DEFAULT_SMOKE_CASES)


def test_pre_release_audit_names_every_unverified_live_tool() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    selected = {case.tool for case in DEFAULT_SMOKE_CASES}
    missing = CURRENT_PUBLIC_TOOLS - selected
    assert "13" in text and "12" in text and "25" in text and "37" in text
    assert "not 37/37" in text.lower()
    for name in sorted(missing):
        assert f"`{name}`" in text
