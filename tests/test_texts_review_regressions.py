from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.texts import TextParseError, parse_text_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/get_a_chapter.php?file=71026&page=0",
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )


def test_navigation_without_pagination_marker_is_parser_drift() -> None:
    body = (
        (FIXTURES / "text_page_bt_az.html")
        .read_bytes()
        .replace(b"<div>Page 1 of 50 (2413 lines total)</div>", b"")
    )

    with pytest.raises(TextParseError):
        parse_text_page(
            _response(body),
            requested_file_id="71026",
            requested_subtext_id=None,
            requested_page=1,
        )


def test_navigation_for_different_file_is_parser_drift() -> None:
    body = b"""<html><body>
<a href="/get_file_info.php?coord=71026">71026: BT AZ</a>
<div>Page 1 of 50 (2413 lines total)</div>
<a href="get_a_chapter.php?file=99999&amp;sub=&amp;page=1">next page</a>
<div>01 <a href="bablex.php?coord=7102600000001&amp;word=0">xd</a></div>
</body></html>"""

    with pytest.raises(TextParseError):
        parse_text_page(
            _response(body),
            requested_file_id="71026",
            requested_subtext_id=None,
            requested_page=1,
        )


def test_nonadjacent_navigation_target_is_parser_drift() -> None:
    body = b"""<html><body>
<a href="/get_file_info.php?coord=71026">71026: BT AZ</a>
<div>Page 1 of 50 (2413 lines total)</div>
<a href="get_a_chapter.php?file=71026&amp;sub=&amp;page=2">next page</a>
<div>01 <a href="bablex.php?coord=7102600000001&amp;word=0">xd</a></div>
</body></html>"""

    with pytest.raises(TextParseError):
        parse_text_page(
            _response(body),
            requested_file_id="71026",
            requested_subtext_id=None,
            requested_page=1,
        )
