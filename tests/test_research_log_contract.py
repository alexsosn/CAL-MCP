from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research.md"
_RESEARCH_ID_RE = re.compile(r"^## (R-\d{3}) — ", re.MULTILINE)


def test_durable_research_ids_are_unique() -> None:
    ids = _RESEARCH_ID_RE.findall(RESEARCH.read_text(encoding="utf-8"))
    duplicates = sorted(identifier for identifier, count in Counter(ids).items() if count > 1)

    assert duplicates == []
