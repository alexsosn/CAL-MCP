"""Issue #261: CAL leaves ``<dial>`` unclosed inside ``<sup>`` in token sense outlines (R-080)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.token_analysis import TokenAnalysisParseError, parse_token_analysis_page

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "token_analysis_unclosed_dial_current.html"
UNCLOSED = '<sup><dial title="except for OA">-OA</sup>'


def _parse(body: str):
    return parse_token_analysis_page(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/getlex.php?coord=620430101&word=1",
            body=body.encode(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )
    )


def _fixture() -> str:
    body = FIXTURE.read_text(encoding="utf-8")
    assert UNCLOSED in body
    return body


def test_unclosed_dial_in_the_sense_outline_keeps_the_linked_candidate() -> None:
    page = _parse(_fixture())

    assert [
        (c.analysis_label, c.lemma.lemma_key if c.lemma else None) for c in page.candidates
    ] == [(")yt verb G", ")yt V")]
    assert page.unlinked_summaries == ()


@pytest.mark.parametrize(
    "replacement",
    [
        # Other elements left unclosed inside <sup> are not tolerated.
        '<sup><span title="except for OA">-OA</sup>',
        "<sup><b>-OA</sup>",
        # An unclosed dial not directly inside the closing element.
        '<sup><i><dial title="except for OA">-OA</sup>',
        # A dial left open with nothing closing its parent before the <hr>.
        '<dial title="except for OA">-OA',
    ],
)
def test_other_unclosed_outline_elements_still_fail_closed(replacement: str) -> None:
    with pytest.raises(TokenAnalysisParseError):
        _parse(_fixture().replace(UNCLOSED, replacement, 1))


def test_loose_text_after_the_outline_still_fails_closed() -> None:
    body = _fixture().replace("<br></small><hr>", "<br></small>stray text<hr>", 1)

    with pytest.raises(TokenAnalysisParseError):
        _parse(body)
