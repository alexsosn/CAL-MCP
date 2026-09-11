from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon_citation_context import (
    LexiconCitationContextParseError,
    parse_lexicon_citation_context_page,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(body: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/showachapter.php?fullcoord=31000424",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
    )


def test_foreign_source_information_route_fails_closed() -> None:
    html = (_FIXTURES / "lexicon_citation_context_ezra_4_24.html").read_text(encoding="utf-8")
    html = html.replace(
        "/get_file_info.php?coord=310004",
        "https://example.org/get_file_info.php?coord=310004",
        1,
    )

    with pytest.raises(LexiconCitationContextParseError):
        parse_lexicon_citation_context_page(
            _response(html),
            requested_full_coordinate="31000424",
        )


def test_nested_token_endpoint_lookalike_fails_closed() -> None:
    html = (_FIXTURES / "lexicon_citation_context_ezra_4_24.html").read_text(encoding="utf-8")
    html = html.replace(
        "getlex.php?coord=31000424&word=0",
        "nested/getlex.php?coord=31000424&word=0",
        1,
    )

    with pytest.raises(LexiconCitationContextParseError):
        parse_lexicon_citation_context_page(
            _response(html),
            requested_full_coordinate="31000424",
        )


def test_unlinked_rendered_text_is_preserved_in_line_text() -> None:
    html = (_FIXTURES / "lexicon_citation_context_ezra_4_24.html").read_text(encoding="utf-8")
    html = html.replace(
        '<a href="getlex.php?coord=31000424&word=0">target-one</a>\n      '
        '<a href="getlex.php?coord=31000424&word=1">target-two</a>',
        '<a href="getlex.php?coord=31000424&word=0">target-one</a> — unlinked-note '
        '<a href="getlex.php?coord=31000424&word=1">target-two</a>',
        1,
    )

    page = parse_lexicon_citation_context_page(
        _response(html),
        requested_full_coordinate="31000424",
    )

    target = next(line for line in page.lines if line.coordinate == "31000424")
    assert target.text == "target-one — unlinked-note target-two"
