"""Issue #203: Babylonian Talmud full-context rows use bablex.php token links.

See docs/research/issue-203-bablex-full-context.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    KwicFullContextPage,
    KwicFullContextStatus,
    parse_kwic_full_context_page,
)

FIXTURE = (
    Path(__file__).parent / "fixtures" / "cal" / "kwic_full_context_bt_71002_01051_current.html"
)
URL = "https://cal.huc.edu/get_a_kwicchapter.php?file=71002&sub=01051&cset=H&target=7100201051217"
TARGET = "7100201051217"


def _parse(body: bytes) -> KwicFullContextPage:
    return parse_kwic_full_context_page(
        CalResponse(
            status_code=200,
            url=URL,
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
        ),
        requested_file_id="71002",
        requested_subtext_id="01051",
        requested_target_coordinate=TARGET,
        requested_charset="H",
    )


def test_babylonian_talmud_full_context_is_found() -> None:
    page = _parse(FIXTURE.read_bytes())

    assert page.status is KwicFullContextStatus.FOUND
    assert [line.coordinate for line in page.lines] == [
        "7100201051127",
        TARGET,
        "7100201051218",
    ]
    target = page.lines[1]
    assert [(token.word_index, token.text) for token in target.tokens] == [
        (0, '"מאי'),
        (1, "נאקה"),
        (2, 'בחטם";'),
        (3, "נאקתא"),
    ]
    assert target.tokens[0].lexical_url == (
        "https://cal.huc.edu/bablex.php?coord=7100201051217&word=0"
    )
    assert target.display_coordinate == "ms01 pg051 sd2 ln17"
    assert target.comment_url == "https://cal.huc.edu/comment.php?coord=7100201051217"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # CAL's bablex links carry exactly coord and word
        (b"coord=7100201051217&word=1", b"coord=7100201051217&word=1&hasvariant=0"),
        (b"coord=7100201051217&word=1", b"coord=7100201051217&word=1&x=1"),
        (b"coord=7100201051217&word=1", b"coord=7100201051217"),
        # a row mixing the two endpoint families
        (
            b"bablex.php?coord=7100201051217&word=1",
            b"getlex.php?coord=7100201051217&word=1&hasvariant=0",
        ),
        # a token naming another coordinate
        (b"coord=7100201051217&word=1", b"coord=7100201051218&word=1"),
    ],
)
def test_malformed_bablex_rows_fail_closed(old: bytes, new: bytes) -> None:
    body = FIXTURE.read_bytes()
    assert old in body

    with pytest.raises(ConcordanceParseError):
        _parse(body.replace(old, new, 1))
