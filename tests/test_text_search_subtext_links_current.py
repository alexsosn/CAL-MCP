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
PESHITTA = FIXTURES / "text_search_peshitta_unicode_current.html"
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


def _shape(match):
    return (
        match.file_id,
        match.subtext_id,
        match.category_id,
        match.follow_up_tool,
    )


def test_neofiti_is_a_catalogue_node() -> None:
    (match,) = _parse(NEOFITI.read_bytes()).matches

    assert _shape(match) == (None, None, "54001", "cal_text_catalogue")
    assert match.label == "TN (Targum Neofiti)"
    assert match.description is not None
    assert match.description.startswith("book 1 chapter 2 verse 2")


def test_onkelos_result_names_a_catalogue_node_not_a_file() -> None:
    (match,) = _parse(ONKELOS.read_bytes()).matches

    assert _shape(match) == (None, None, "70703012", "cal_text_catalogue")
    assert match.label == "HS 3030"


def test_peshitta_mixes_text_links_and_unicode_catalogue_nodes() -> None:
    matches = _parse(PESHITTA.read_bytes()).matches

    assert [_shape(match) for match in matches] == [
        ("62018", None, None, "cal_text_page"),
        (None, None, "62001", "cal_text_catalogue"),
        (None, None, "62002", "cal_text_catalogue"),
        (None, None, "6203504", "cal_text_catalogue"),
    ]


def test_mandaic_subdivided_results_are_catalogue_nodes() -> None:
    matches = _parse(GINZA.read_bytes()).matches

    assert [_shape(match) for match in matches] == [
        (None, None, "74410", "cal_text_catalogue"),
        (None, None, "74411", "cal_text_catalogue"),
    ]


def test_mandaic_collection_link_in_roman_script_is_still_a_catalogue_node() -> None:
    body = GINZA.read_bytes().replace(b"subtext=74410&amp;cset=M", b"subtext=74410&amp;cset=R")

    assert _shape(_parse(body).matches[0]) == (None, None, "74410", "cal_text_catalogue")


@pytest.mark.parametrize(
    ("href", "message"),
    [
        (b"/showsubtexts.php?subtext=54001&cset=X", "invalid cset"),
        (b"/showsubtexts.php?subtext=54001", "invalid cset"),
        (b"/showsubtexts.php?subtext=54001&cset=H&cset=R", "invalid cset"),
        (b"/showsubtexts.php?subtext=5400a&cset=H", "invalid file identifier"),
        # Mandaic selector outside the Mandaic collection
        (b"/showsubtexts.php?subtext=54001&cset=M", "invalid cset"),
    ],
)
def test_unrecognised_subtext_links_fail_closed(href: bytes, message: str) -> None:
    body = NEOFITI.read_bytes().replace(b"/showsubtexts.php?subtext=54001&cset=H", href)

    with pytest.raises(TextParseError, match=message):
        _parse(body)


def test_mandaic_collection_link_in_another_script_fails_closed() -> None:
    body = GINZA.read_bytes().replace(b"subtext=74410&amp;cset=M", b"subtext=74410&amp;cset=H")

    with pytest.raises(TextParseError, match="invalid cset"):
        _parse(body)


def test_search_match_fields_are_serialized() -> None:
    page = _parse(PESHITTA.read_bytes())
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
    assert matches[0]["file_id"] == "62018"
    assert matches[0]["category_id"] is None
    assert matches[0]["follow_up_tool"] == "cal_text_page"
    assert matches[1]["file_id"] is None
    assert matches[1]["category_id"] == "62001"
    assert matches[1]["follow_up_tool"] == "cal_text_catalogue"
