"""Issue #151: citation context for texts whose tokens use CAL's bablex.php family.

See docs/research/issue-151-citation-context-bablex.md (and R-024 for text pages).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.lexicon_citation_context import (
    LexiconCitationContextParseError,
    LexiconCitationContextStatus,
    parse_lexicon_citation_context_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
URL = "https://cal.huc.edu/showachapter.php?fullcoord=7101801048150"
TARGET = "7101801048150"


def _body() -> str:
    return (FIXTURES / "lexicon_citation_context_bt_git_48a50.html").read_text(encoding="utf-8")


def _parse(body: str) -> object:
    return parse_lexicon_citation_context_page(
        CalResponse(
            status_code=200,
            url=URL,
            body=body.encode(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 24, tzinfo=UTC),
        ),
        requested_full_coordinate=TARGET,
    )


def test_babylonian_talmud_citation_context_parses_bablex_rows() -> None:
    page = _parse(_body())

    assert page.status is LexiconCitationContextStatus.FOUND  # type: ignore[attr-defined]
    assert page.source_label == "71018: BT Git"  # type: ignore[attr-defined]
    lines = page.lines  # type: ignore[attr-defined]
    assert [line.coordinate for line in lines] == ["7101801048149", TARGET, "7101801048204"]
    target = lines[1]
    assert target.display_coordinate == "ms01 pg048 sd1 ln50"
    assert target.comment_url == "https://cal.huc.edu/comment.php?coord=7101801048150"
    assert [token.text for token in target.tokens] == ["אלא", "חד", "בר"]
    assert target.tokens[2].lexical_url == (
        "https://cal.huc.edu/bablex.php?coord=7101801048150&word=2"
    )


def test_row_mixing_lexical_token_families_fails_closed() -> None:
    body = _body().replace(
        '<a href="bablex.php?coord=7101801048150&word=1"',
        '<a href="getlex.php?coord=7101801048150&word=1"',
    )
    with pytest.raises(LexiconCitationContextParseError, match="mixes lexical token families"):
        _parse(body)


def test_bablex_token_with_unexpected_query_fails_closed() -> None:
    body = _body().replace(
        "bablex.php?coord=7101801048150&word=1",
        "bablex.php?coord=7101801048150&word=1&hasvariant=0",
    )
    with pytest.raises(LexiconCitationContextParseError, match="unexpected query semantics"):
        _parse(body)
