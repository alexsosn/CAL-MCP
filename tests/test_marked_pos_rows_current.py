from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.errors import CalParseError
from cal_mcp.lexicon import parse_browse_page, parse_lexicon_entry
from cal_mcp.lexicon_browse import parse_lexicon_browse_page
from cal_mcp.search import parse_gloss_search_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 10, 8, 19, 17, tzinfo=UTC)


def _response(body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/browseSKEYheaders.php",
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _rows(lemmas: tuple[object, ...]) -> list[tuple[object, ...]]:
    return [
        (item.lemma_key, item.headwords, item.part_of_speech, item.gloss)  # type: ignore[attr-defined]
        for item in lemmas
    ]


_BROWSE_EXPECTED = [
    ("(hr V", ("ˁHR", "ˀHR"), "vb. a/u", "to be sexually aroused"),
    ("(hr A", ("ˁhr",), "adj.", "lustful"),
]


def test_lexicon_browse_keeps_cal_marked_verb_vowel_class() -> None:
    page = parse_lexicon_browse_page(_response(_fixture("browse_verb_vowel_class.html").encode()))

    assert _rows(page.entries) == _BROWSE_EXPECTED


def test_lookup_browse_step_keeps_cal_marked_verb_vowel_class() -> None:
    page = parse_browse_page(_response(_fixture("browse_verb_vowel_class.html").encode()))

    assert _rows(page.entries) == _BROWSE_EXPECTED


def test_gloss_field_keeps_cal_marked_verb_vowel_class() -> None:
    page = parse_gloss_search_page(_response(_fixture("search_gloss_field_verb_pos.html").encode()))

    assert _rows(tuple(m.lemma for m in page.matches)) == [
        ("x$l#2 V", ("ḤŠL",), "vb. a(i)/u", "to fabricate"),
        ("$xl V", ("ŠḤL",), "vb. a/u, e/a", "to drip; draw out of liquid"),
    ]


_PARSERS = [
    ("browse_verb_vowel_class.html", parse_lexicon_browse_page),
    ("browse_verb_vowel_class.html", parse_browse_page),
    ("search_gloss_field_verb_pos.html", parse_gloss_search_page),
]


@pytest.mark.parametrize(("fixture", "parser"), _PARSERS)
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # Two <pos> elements in one lemma link.
        ("</pos>", "</pos><pos>n.m.</pos>"),
        # A POS-looking headword token makes the header grammar disagree with the marked POS.
        ("</font>", " x.y.</font>"),
        # Unexplained rendered text after the marked POS inside the link.
        ("</pos>", "</pos> stray"),
        # A homograph marker inside the marked POS, or a <pos> left unclosed.
        ("</pos>", " #2</pos>"),
        ("</pos>", ""),
    ],
)
def test_marked_pos_disagreement_fails_closed(
    fixture: str, parser: object, old: str, new: str
) -> None:
    body = _fixture(fixture)
    assert old in body
    with pytest.raises(CalParseError):
        parser(_response(body.replace(old, new, 1).encode()))  # type: ignore[operator]


def test_exact_entry_keeps_cal_vocalized_vowel_class_as_pronunciation() -> None:
    body = (
        '<div class="lemma-header"><span class="lemma-formal"><b>ˁhr, ˀhr</b></span> '
        '<span class="lemma-vocalized">(a/u)</span> <span class="lemma-pos">vb.</span> '
        '<span class="lemma-gloss"><b>to be sexually aroused</b></span></div>'
        "<div>1</div><div>to be sexually aroused</div><div>Syriac</div>"
    )
    entry = parse_lexicon_entry(_response(body.encode()), lemma_key="(hr V")

    assert entry.lemma.part_of_speech == "vb."
    assert entry.lemma.pronunciation == "a/u"
