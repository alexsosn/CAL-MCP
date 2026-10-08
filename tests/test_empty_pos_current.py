from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.errors import CalParseError
from cal_mcp.lexicon import LexiconParseError, parse_browse_page, parse_lexicon_entry
from cal_mcp.lexicon_browse import parse_lexicon_browse_page
from cal_mcp.search import _gloss_match_to_dict, parse_gloss_search_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 10, 8, 19, 30, tzinfo=UTC)


def _response(body: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/browseSKEYheaders.php",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _row(lemma: object) -> tuple[object, ...]:
    return (
        lemma.lemma_key,  # type: ignore[attr-defined]
        lemma.headwords,  # type: ignore[attr-defined]
        lemma.pronunciation,  # type: ignore[attr-defined]
        lemma.part_of_speech,  # type: ignore[attr-defined]
        lemma.gloss,  # type: ignore[attr-defined]
    )


_EMPTY_POS_ROW = ("$yp#2 N", ("šyp", "šypˀ"), None, None, "a type of marsh reed")


def test_gloss_field_row_with_empty_cal_pos_has_null_part_of_speech() -> None:
    page = parse_gloss_search_page(_response(_fixture("search_gloss_field_empty_pos.html")))

    assert [_row(m.lemma) for m in page.matches] == [
        _EMPTY_POS_ROW,
        ("$yc N", ("šyṣ", "šyṣˀ"), None, "n.m.", page.matches[1].lemma.gloss),
    ]
    assert _gloss_match_to_dict(page.matches[0])["part_of_speech"] is None


@pytest.mark.parametrize("parser", [parse_lexicon_browse_page, parse_browse_page])
def test_browse_row_with_empty_cal_pos_has_null_part_of_speech(parser: object) -> None:
    page = parser(_response(_fixture("browse_empty_pos_current.html")))  # type: ignore[operator]

    assert _row(page.entries[0]) == _EMPTY_POS_ROW
    assert page.entries[1].lemma_key == "$yp A"
    assert page.entries[1].part_of_speech is not None


_ROW_FIXTURES = [
    ("search_gloss_field_empty_pos.html", parse_gloss_search_page),
    ("browse_empty_pos_current.html", parse_lexicon_browse_page),
    ("browse_empty_pos_current.html", parse_browse_page),
]


@pytest.mark.parametrize(("fixture", "parser"), _ROW_FIXTURES)
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # An empty <pos> contradicted by a POS-looking token in the rendered header.
        ("šyp, šypˀ</font>", "šyp, n.m.</font>"),
        # Two <pos> elements, one empty.
        ("<pos></pos>", "<pos></pos><pos>n.m.</pos>"),
        # Unexplained text after the empty <pos>, other than the homograph marker.
        ("<pos></pos>", "<pos></pos> stray"),
    ],
)
def test_empty_pos_disagreement_fails_closed(
    fixture: str, parser: object, old: str, new: str
) -> None:
    body = _fixture(fixture)
    assert old in body
    with pytest.raises(CalParseError):
        parser(_response(body.replace(old, new, 1)))  # type: ignore[operator]


def test_current_entry_header_without_pos_fails_closed_instead_of_taking_a_later_line() -> None:
    # Minimal synthetic sense lines make the rest of the page parseable, so that only the header
    # decides the outcome.
    body = _fixture("entry_lemma_header_no_pos_current.html").replace(
        "</body>", "<div>1</div><div>a type of marsh reed</div><div>JBA</div></body>"
    )
    with pytest.raises(LexiconParseError, match="lemma-header"):
        parse_lexicon_entry(_response(body), lemma_key="$yp#2 N")


def test_current_entry_lemma_header_still_parses() -> None:
    body = (
        '<div class="lemma-header"><span class="lemma-formal"><b>ˁhr, ˀhr</b></span> '
        '<span class="lemma-vocalized">(a/u)</span> <span class="lemma-pos">vb.</span> '
        '<span class="lemma-gloss"><b>to be sexually aroused</b></span></div>'
        "<div>1</div><div>to be sexually aroused</div><div>Syriac</div>"
    )
    entry = parse_lexicon_entry(_response(body), lemma_key="(hr V")

    assert (entry.lemma.headwords, entry.lemma.part_of_speech, entry.lemma.pronunciation) == (
        ("ˁhr", "ˀhr"),
        "vb.",
        "a/u",
    )
