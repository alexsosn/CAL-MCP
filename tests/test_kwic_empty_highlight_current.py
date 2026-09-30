"""Issue #204: KWIC target lines where CAL's highlight marks nothing.

See docs/research/issue-204-empty-kwic-highlight.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import ConcordanceParseError, KwicPage, KwicScopeKind, parse_kwic_result

FIXTURE = (
    Path(__file__).parent / "fixtures" / "cal" / "kwic_texts_mlk_56000_empty_highlight_current.html"
)


def _parse(body: bytes) -> KwicPage:
    return parse_kwic_result(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/showdialectKWIC.php",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
        ),
        lemma_key="mlk N",
        scope_kind=KwicScopeKind.TEXTS,
        scope_ids=("56000",),
    )


def test_empty_highlight_is_returned_as_null_target_text() -> None:
    page = _parse(FIXTURE.read_bytes())

    assert page.total == 4
    assert [hit.target_text for hit in page.hits] == ["mlK", "w)rywK", ")l)sr", None]
    empty = page.hits[3]
    assert (empty.file_id, empty.subtext_id, empty.target_coordinate) == (
        "56000",
        "114",
        "56000114010",
    )
    assert empty.full_context_url == (
        "https://cal.huc.edu/get_a_kwicchapter.php?file=56000&sub=114&cset=R&target=56000114010"
    )
    assert empty.context.startswith("whwh bywmy )mrpl")


_EMPTY = b"mlK &nbsp;&nbsp;<b>&nbsp;&nbsp; </b>(ylM"


@pytest.mark.parametrize(
    "replacement",
    [
        b"mlK (ylM",  # no highlight at all
        b"mlK &nbsp;&nbsp;<b>&nbsp;&nbsp; </b><b>(ylM</b>",  # two highlights
    ],
)
def test_missing_or_repeated_highlight_still_fails_closed(replacement: bytes) -> None:
    body = FIXTURE.read_bytes()
    assert _EMPTY in body

    with pytest.raises(ConcordanceParseError):
        _parse(body.replace(_EMPTY, replacement))
