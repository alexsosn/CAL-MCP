from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.texts import TextParseError, parse_text_line_comments_page

_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_line_comments_pj_gen8_21.html"
_COORDINATE = "8100110821"
_SOURCE_URL = f"https://cal.huc.edu/comment.php?coord={_COORDINATE}"
_ENTRY_HREF = "/oneentry.php?lemma=qbl+V&amp;cits=all"


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


def test_malformed_returned_lemma_key_fails_closed() -> None:
    original = _FIXTURE.read_text(encoding="utf-8")
    assert original.count(_ENTRY_HREF) == 1
    body = original.replace(
        _ENTRY_HREF,
        "/oneentry.php?lemma=not-a-key&amp;cits=all",
        1,
    )

    with pytest.raises(TextParseError):
        parse_text_line_comments_page(_response(body), requested_coordinate=_COORDINATE)
