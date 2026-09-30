"""Issue #171: non-Mandaic showsubtexts.php links in text search results.

See docs/research/issue-171-text-search-subtext-links.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.texts import (
    TextParseError,
    TextProvenance,
    TextSearchResult,
    parse_text_search_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
NEOFITI = FIXTURES / "text_search_neofiti_subtexts_current.html"
ONKELOS = FIXTURES / "text_search_onkelos_subtexts_current.html"
GINZA = FIXTURES / "text_search_ginza.html"


def _parse(body: bytes):
    return parse_text_search_page(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/newsearchtxts.php",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 30, tzinfo=UTC),
        )
    )


def test_neofiti_is_a_catalogue_node_followed_with_the_catalogue() -> None:
    (match,) = _parse(NEOFITI.read_bytes()).matches

    assert (match.file_id, match.subtext_id, match.label, match.follow_with) == (
        "54001",
        None,
        "TN (Targum Neofiti)",
        "cal_text_catalogue",
    )
    assert match.description is not None
    assert match.description.startswith("book 1 chapter 2 verse 2")


def test_onkelos_search_result_is_followed_with_the_catalogue() -> None:
    (match,) = _parse(ONKELOS.read_bytes()).matches

    assert (match.file_id, match.label, match.follow_with) == (
        "70703012",
        "HS 3030",
        "cal_text_catalogue",
    )


def test_mandaic_results_are_still_followed_with_the_text_page() -> None:
    matches = _parse(GINZA.read_bytes()).matches

    assert matches
    assert {match.follow_with for match in matches} == {"cal_text_page"}


def test_ordinary_text_links_are_followed_with_the_text_page() -> None:
    body = NEOFITI.read_bytes().replace(
        b'href="/showsubtexts.php?subtext=54001&cset=H"',
        b'href="/get_a_chapter.php?file=54001&sub=101"',
    )
    (match,) = _parse(body).matches

    assert (match.file_id, match.subtext_id, match.follow_with) == ("54001", "101", "cal_text_page")


@pytest.mark.parametrize(
    "href",
    [
        b"/showsubtexts.php?subtext=54001&cset=X",
        b"/showsubtexts.php?subtext=54001",
        b"/showsubtexts.php?subtext=5400a&cset=H",
        b"/showsubtexts.php?subtext=54001&cset=H&cset=R",
    ],
)
def test_unrecognised_subtext_links_fail_closed(href: bytes) -> None:
    body = NEOFITI.read_bytes().replace(b"/showsubtexts.php?subtext=54001&cset=H", href)

    with pytest.raises(TextParseError):
        _parse(body)


def test_follow_with_is_serialized() -> None:
    page = _parse(NEOFITI.read_bytes())
    result = TextSearchResult(
        matches=page.matches,
        provenance=TextProvenance(
            source="CAL",
            source_url="https://cal.huc.edu/newsearchtxts.php",
            retrieved_at=datetime(2026, 9, 30, tzinfo=UTC),
            operation="search",
        ),
    )

    matches = result.to_dict()["matches"]
    assert isinstance(matches, list)
    assert matches[0]["follow_with"] == "cal_text_catalogue"
