from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research.md"
_PESHITTA_RESEARCH_HEADING_RE = re.compile(
    r"^## (R-\d{3}) — Current Syriac Peshitta book rows use shallow catalogue navigation$",
    re.MULTILINE,
)


def test_peshitta_research_record_uses_next_durable_id() -> None:
    ids = _PESHITTA_RESEARCH_HEADING_RE.findall(RESEARCH.read_text(encoding="utf-8"))

    assert ids == ["R-026"]
