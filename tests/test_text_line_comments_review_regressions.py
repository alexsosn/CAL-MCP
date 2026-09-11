from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.texts import TextParseError, parse_text_line_comments_page

_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_line_comments_pj_gen8_21.html"
_COORDINATE = "8100110821"
_SOURCE_URL = f"https://cal.huc.edu/comment.php?coord={_COORDINATE}"
_EMPTY_MARKER = "NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED"


def _response(body: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=_SOURCE_URL,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 10, tzinfo=UTC),
    )


def test_unclosed_line_comment_reference_markup_fails_closed() -> None:
    body = _FIXTURE.read_text(encoding="utf-8").replace("</i>", "", 1)

    with pytest.raises(TextParseError):
        parse_text_line_comments_page(_response(body), requested_coordinate=_COORDINATE)


def test_non_rendered_script_cannot_fabricate_no_citations_state() -> None:
    body = _FIXTURE.read_text(encoding="utf-8")
    summary_start = '<div class="summary-card">'
    before, remainder = body.split(summary_start, 1)
    _old_summary, after = remainder.split("</div>", 1)
    body = (
        f"{before}{summary_start}\n"
        f"  <p><script>{_EMPTY_MARKER}</script></p>\n"
        f"</div>{after}"
    )

    with pytest.raises(TextParseError):
        parse_text_line_comments_page(_response(body), requested_coordinate=_COORDINATE)


def test_nested_summary_card_fails_unique_container_contract() -> None:
    body = _FIXTURE.read_text(encoding="utf-8")
    body = body.replace(
        '<div class="summary-card">',
        '<div class="summary-card"><div class="summary-card">',
        1,
    )
    body = body.replace("</div>", "</div></div>", 1)

    with pytest.raises(TextParseError):
        parse_text_line_comments_page(_response(body), requested_coordinate=_COORDINATE)
