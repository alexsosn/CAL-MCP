"""CAL current Peshitta sense outlines have one unclosed dialect inside sup (#261)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.token_analysis import TokenAnalysisParseError, parse_token_analysis_page

FIXTURE = (
    Path(__file__).parent / "fixtures" / "cal" / "token_analysis_multi_lexeme_verb_current.html"
)
_NEEDLE = '<p><span class="bin">G</span>'
_CAL_DIALECT = '<span class="dial-tag"><sup><dial title="except for OA">-OA</sup></span>'


def _mutated(extra: str) -> CalResponse:
    body = FIXTURE.read_text(encoding="utf-8")
    assert _NEEDLE in body
    body = body.replace(_NEEDLE, _NEEDLE + extra, 1)
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getlex.php?coord=620430101&word=1",
        body=body.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
    )


def test_current_peshitta_unclosed_dial_within_sup_preserves_linked_candidates() -> None:
    page = parse_token_analysis_page(_mutated(_CAL_DIALECT))
    assert [candidate.lemma.lemma_key for candidate in page.candidates] == [
        "w_ c",
        ")mr V",
    ]
    assert page.unlinked_summaries == ()


@pytest.mark.parametrize(
    "unexpected",
    [
        '<span class="dial-tag"><sup><i>-OA</sup></span>',
        '<span class="dial-tag"><dial>-OA</span>',
        '<span class="dial-tag"><sup><dial>-OA<hr></sup></span>',
    ],
)
def test_other_unclosed_or_internal_hr_still_fails_closed(unexpected: str) -> None:
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_mutated(unexpected))
