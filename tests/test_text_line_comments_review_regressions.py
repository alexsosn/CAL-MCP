from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.texts import TextParseError, parse_text_line_comments_page

_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_line_comments_pj_gen8_21.html"
_COORDINATE = "8100110821"


def test_unclosed_line_comment_reference_markup_fails_closed() -> None:
    body = _FIXTURE.read_text(encoding="utf-8").replace("</i>", "", 1)
    response = CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/comment.php?coord={_COORDINATE}",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 10, tzinfo=UTC),
    )

    with pytest.raises(TextParseError):
        parse_text_line_comments_page(response, requested_coordinate=_COORDINATE)
