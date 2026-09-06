from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import LexiconParseError, parse_browse_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
BROWSE_URL = "https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22"


def _response(html: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=BROWSE_URL,
        body=html.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 6, 19, 16, tzinfo=UTC),
    )


def test_current_browse_shape_recovers_unclosed_jump_anchors_without_losing_candidates() -> None:
    html = (FIXTURES / "browse_br_unclosed_jump_2026_09_06.html").read_text(
        encoding="utf-8"
    )

    browse = parse_browse_page(_response(html))

    assert [entry.lemma_key for entry in browse.entries] == ["br N", "br#2 N"]
    assert browse.entries[0].headwords == ("br", "brˀ")
    assert browse.entries[0].part_of_speech == "n.m."
    assert browse.entries[0].gloss == "son"
    assert browse.entries[1].part_of_speech == "n.f."
    assert browse.entries[1].gloss == "field, outside"


def test_candidate_like_link_missing_required_pos_fails_closed_instead_of_partial_result() -> None:
    html = """
    <html><body>
      <div><a href="oneentry.php?lemma=br N&cits=all">br, brˀ (bar, brā) n.m.</a></div>
      <div>son</div>
      <div><a href="oneentry.php?lemma=br%232 N&cits=all">br, brˀ (bar, barrā) #2</a></div>
      <div>field, outside</div>
    </body></html>
    """

    with pytest.raises(LexiconParseError, match="candidate"):
        parse_browse_page(_response(html))


def test_candidate_like_entry_handler_without_lemma_key_fails_closed() -> None:
    html = """
    <html><body>
      <div><a href="oneentry.php?lemma=br N&cits=all">br, brˀ (bar, brā) n.m.</a></div>
      <div>son</div>
      <div><a href="oneentry.php?cits=all">malformed candidate</a></div>
    </body></html>
    """

    with pytest.raises(LexiconParseError, match="candidate"):
        parse_browse_page(_response(html))
