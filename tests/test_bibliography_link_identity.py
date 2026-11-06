"""Issue #328: reject ambiguous CAL bibliography navigation identities without a live fetch.

Grounding: reduced current CAL bibliography fixture hrefs, researched 2026-11-07.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.bibliography import (
    BibliographyParseError,
    BibliographyQueryKind,
    parse_bibliography_page,
    parse_recent_bibliography_page,
)
from cal_mcp.client import CalResponse

URL = "https://cal.huc.edu/getbibsigla.php?myauthor=TADA"


def _response(href: str, *, label: str = "CAL tag", recent: bool = False) -> CalResponse:
    heading = "CAL Recent Bibliography" if recent else "CAL Bibliography for TADA"
    html = (
        f"<html><body><h1>{heading}</h1>"
        f'<div class="card"><p>A bibliography citation. <a href="{href}">{label}</a></p></div>'
        "</body></html>"
    )
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getrecentbib.php" if recent else URL,
        body=html.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 11, 7, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    "href",
    [
        "/getbibsigla.php?myauthor=TADA&mode=changed",
        "/getbibsigla.php?myauthor=TADA&mode=",
        "/getbibsigla.php?myauthor=TADA&myauthor=JBA",
        "/archive/getbibsigla.php?myauthor=TADA",
        "/./getbibsigla.php?myauthor=TADA",
        "/getbibsigla.php?myauthor=TADA#other",
        "/getbibsigla.php?myauthor=%ZZ",
        "/getbibsigla.php?myauthor=%FF",
        "/getbibsigla.php?myauthor=TADA&&",
        "/getbibsigla.php?myauthor=TADA&",
    ],
)
@pytest.mark.parametrize("recent", [False, True])
def test_noncanonical_typed_bibliography_links_fail_closed(href: str, recent: bool) -> None:
    response = _response(href, recent=recent)
    with pytest.raises(BibliographyParseError):
        if recent:
            parse_recent_bibliography_page(response)
        else:
            parse_bibliography_page(response)


@pytest.mark.parametrize(
    ("href", "kind", "value"),
    [
        ("/getbibsigla.php?myauthor=TADA", BibliographyQueryKind.KEYWORD, "TADA"),
        ("getbibsigla.php?myauthor=Loanwords", BibliographyQueryKind.KEYWORD, "Loanwords"),
        (
            "https://cal.huc.edu/getbibauthor.php?myauthor=Kaufman%2C+Stephen+A.",
            BibliographyQueryKind.AUTHOR,
            "Kaufman, Stephen A.",
        ),
        ("/getbiblemma.php?myauthor=%29wwr+N", BibliographyQueryKind.LEMMA, ")wwr N"),
        ("/getbibsigla.php?myauthor=Caf%C3%A9", BibliographyQueryKind.KEYWORD, "Café"),
        ("/getbibsigla.php?myauthor=שלום", BibliographyQueryKind.KEYWORD, "שלום"),
    ],
)
def test_canonical_links_preserve_exact_cal_value(
    href: str, kind: BibliographyQueryKind, value: str
) -> None:
    record = parse_bibliography_page(_response(href)).records[0]
    assert record.links[0].query_kind is kind
    assert record.links[0].query_value == value
    assert record.links[0].label == "CAL tag"
    assert record.links[0].url.startswith("https://cal.huc.edu/getbib")


def test_unrelated_same_origin_link_remains_generic() -> None:
    record = parse_bibliography_page(_response("/getlex.php?lemma=br+N")).records[0]
    assert record.links[0].query_kind is None
    assert record.links[0].query_value is None
    assert record.links[0].url == "https://cal.huc.edu/getlex.php?lemma=br+N"


def test_empty_cal_placeholder_still_has_no_semantics() -> None:
    record = parse_bibliography_page(_response("/getbiblemma.php?myauthor=", label="")).records[0]
    assert record.citation == "A bibliography citation."
    assert record.links == ()


def test_same_page_query_alias_is_not_canonical_typed_navigation() -> None:
    # This is a typed handler only on the targeted result endpoint; on
    # getrecentbib.php a self-query remains an unrelated generic CAL link.
    with pytest.raises(BibliographyParseError):
        parse_bibliography_page(_response("?myauthor=TADA"))


def test_recent_page_self_query_remains_generic() -> None:
    record = parse_recent_bibliography_page(_response("?myauthor=TADA", recent=True)).records[0]
    assert record.links[0].query_kind is None
    assert record.links[0].url == "https://cal.huc.edu/getrecentbib.php?myauthor=TADA"
