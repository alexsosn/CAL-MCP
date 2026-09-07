from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import parse_browse_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def test_current_browse_recovers_candidates_after_unclosed_jump_anchors() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22",
        body=(FIXTURES / "browse_br_unclosed_jump_anchors.html").read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 6, 18, 12, tzinfo=UTC),
    )

    page = parse_browse_page(response)

    assert [entry.lemma_key for entry in page.entries] == ["br N", "br#2 N"]
    assert page.entries[0].headwords == ("br", "brˀ")
    assert page.entries[0].pronunciation == "bar (ber), brā"
    assert page.entries[0].part_of_speech == "n.m."
    assert page.entries[0].gloss == "son"
    assert page.entries[1].part_of_speech == "n.f."
    assert page.entries[1].gloss == "field, outside"
