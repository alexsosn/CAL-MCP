from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import parse_browse_page, parse_lexicon_entry

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(body: bytes, *, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )


def _inline_style_entry():
    return parse_lexicon_entry(
        _response(
            (FIXTURES / "entry_b_inline_style.html").read_bytes(),
            url="https://cal.huc.edu/cal_entry_web.php?lemma=b+s",
        ),
        lemma_key="b s",
    )


def test_inline_style_and_script_are_excluded_from_entry_text() -> None:
    entry = _inline_style_entry()

    assert entry.lemma.headwords == ("b",)
    assert entry.lemma.part_of_speech == "sym."
    assert entry.lemma.gloss == "second letter of alphabet"
    assert len(entry.senses) == 8

    rendered = repr(entry)
    for forbidden in ("fullentry.css", "@font-face", "/*", "script.js"):
        assert forbidden not in rendered


def test_full_entry_lemma_agrees_with_matching_browse_candidate() -> None:
    browse = parse_browse_page(
        _response(
            (
                b'<html><body><div><a href="/cal_entry_web.php?lemma=b+s">b sym.</a></div>'
                b"<div>second letter of alphabet</div></body></html>"
            ),
            url='https://cal.huc.edu/browseSKEYheaders.php?first3=%22b%22',
        )
    )
    candidate = next(item for item in browse.entries if item.lemma_key == "b s")
    entry = _inline_style_entry()

    assert entry.lemma.lemma_key == candidate.lemma_key
    assert entry.lemma.headwords == candidate.headwords
    assert entry.lemma.part_of_speech == candidate.part_of_speech
    assert entry.lemma.gloss == candidate.gloss
