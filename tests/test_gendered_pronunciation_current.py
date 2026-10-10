"""Issue #267: CAL numerals carry a gender-labelled pronunciation (``m. …, f. …``).

The ``m.``/``f.`` labels sit inside the parenthesized pronunciation and must never be read as
the row's part of speech (R-079).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon import _parse_lemma_header, parse_browse_page
from cal_mcp.lexicon_browse import parse_lexicon_browse_page
from cal_mcp.search import SearchParseError, parse_gloss_search_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
GLOSS = FIXTURES / "search_gloss_even_numeral_current.html"
BROWSE = FIXTURES / "browse_xd_numeral_current.html"
ELEVEN = ("xd@(sr b", ("ḥd ˁsr",), "m. ḥəḏaˁsar, f. ḥəḏaˁesrē", "num.", "eleven")


def _response(path: Path, url: str, *, body: str | None = None) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(body if body is not None else path.read_text(encoding="utf-8")).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
    )


def _row(lemma: object) -> tuple[object, ...]:
    return (
        lemma.lemma_key,  # type: ignore[attr-defined]
        lemma.headwords,  # type: ignore[attr-defined]
        lemma.pronunciation,  # type: ignore[attr-defined]
        lemma.part_of_speech,  # type: ignore[attr-defined]
        lemma.gloss,  # type: ignore[attr-defined]
    )


def test_gloss_search_keeps_the_numeral_and_the_requested_lemma() -> None:
    page = parse_gloss_search_page(_response(GLOSS, "https://cal.huc.edu/newsearchmngs.php"))

    rows = [_row(match.lemma) for match in page.matches]
    assert rows[0][0] == ")p c"
    assert rows[1] == ELEVEN


@pytest.mark.parametrize("parser", [parse_browse_page, parse_lexicon_browse_page])
def test_browse_keeps_the_numeral_row(parser: object) -> None:
    page = parser(  # type: ignore[operator]
        _response(BROWSE, "https://cal.huc.edu/browseSKEYheaders.php?first3=%22xd%22")
    )

    assert _row(page.entries[0]) == ELEVEN
    assert [entry.lemma_key for entry in page.entries] == ["xd@(sr b", "xdw N", "xdwr)yt X"]


def test_nested_parentheses_inside_the_pronunciation_are_kept_verbatim() -> None:
    # Verbatim header text of CAL's "twelve" (try@(sr b), 2026-10-10.
    lemma = _parse_lemma_header(
        "try ˁsr, trty ˁsry (m. təre(n)ˁsar, f. tartaˁesrē) num.",
        lemma_key="try@(sr b",
        require_gloss=False,
    )

    assert lemma is not None
    assert lemma.headwords == ("try ˁsr", "trty ˁsry")
    assert lemma.pronunciation == "m. təre(n)ˁsar, f. tartaˁesrē"
    assert lemma.part_of_speech == "num."


def test_secondary_gender_pos_tokens_are_unaffected() -> None:
    lemma = _parse_lemma_header(
        "ktb, ktbˀ (kṯāḇ, kṯāḇā) n.m.(f.) book", lemma_key="ktb N", require_gloss=False
    )

    assert lemma is not None
    assert lemma.part_of_speech == "n.m.(f.)"


@pytest.mark.parametrize(
    "text",
    [
        # Unbalanced pronunciation group: no trustworthy split, so no header.
        "ḥd ˁsr (m. ḥəḏaˁsar, f. ḥəḏaˁesrē num.",
        # No POS outside the parentheses.
        "ḥd ˁsr (m. ḥəḏaˁsar, f. ḥəḏaˁesrē)",
    ],
)
def test_headers_without_a_pos_outside_balanced_parentheses_fail(text: str) -> None:
    assert _parse_lemma_header(text, lemma_key="xd@(sr b", require_gloss=False) is None


def test_marked_pos_contradicting_the_header_still_fails_closed() -> None:
    # A rendered POS outside CAL's <pos> element that disagrees with the marked one.
    old = "ḥəḏaˁesrē</span>)\n\t<pos>num.</pos>"
    body = GLOSS.read_text(encoding="utf-8")
    assert old in body
    body = body.replace(old, "ḥəḏaˁesrē</span>) n.m.\n\t<pos>num.</pos>")

    with pytest.raises(SearchParseError):
        parse_gloss_search_page(
            _response(GLOSS, "https://cal.huc.edu/newsearchmngs.php", body=body)
        )
