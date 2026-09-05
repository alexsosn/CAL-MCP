from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import LexiconParseError, parse_browse_page, parse_lexicon_entry

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )


def test_inline_style_and_script_are_not_lexicon_semantic_text() -> None:
    entry = parse_lexicon_entry(
        _response(
            "entry_b_s_inline_style.html",
            "https://cal.huc.edu/cal_entry_web.php?lemma=b+s",
        ),
        lemma_key="b s",
    )

    assert entry.lemma.headwords == ("b",)
    assert entry.lemma.part_of_speech == "sym."
    assert entry.lemma.gloss == "second letter of alphabet"
    assert len(entry.senses) == 8

    serialized = repr(asdict(entry))
    for leaked_noncontent in (
        "fullentry.css",
        "@font-face",
        "/*",
        "CAL_LEXICON_SCRIPT_SENTINEL",
        "must-not-be-semantic-text",
    ):
        assert leaked_noncontent not in serialized


def test_full_entry_lemma_agrees_with_current_browse_candidate() -> None:
    browse = parse_browse_page(
        _response(
            "browse_b_current.html",
            "https://cal.huc.edu/browseSKEYheaders.php?first3=%22b%22",
        )
    )
    entry = parse_lexicon_entry(
        _response(
            "entry_b_s_inline_style.html",
            "https://cal.huc.edu/cal_entry_web.php?lemma=b+s",
        ),
        lemma_key="b s",
    )

    candidate = next(item for item in browse.entries if item.lemma_key == "b s")
    assert entry.lemma.headwords == candidate.headwords
    assert entry.lemma.part_of_speech == candidate.part_of_speech
    assert entry.lemma.gloss == candidate.gloss


def test_unclosed_ignored_subtree_fails_closed_instead_of_returning_partial_entry() -> None:
    html = b"""
    <html><body>
      <header>b sym. second letter of alphabet</header>
      <div>1</div><div>letter name</div>
      <style>.broken { display: none; }
      <div>2</div><div>content after malformed style must not be silently lost</div>
    </body></html>
    """
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/cal_entry_web.php?lemma=b+s",
        body=html,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )

    with pytest.raises(LexiconParseError, match="ignored content subtree"):
        parse_lexicon_entry(response, lemma_key="b s")
