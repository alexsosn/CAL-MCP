from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.concordance import ConcordanceParseError, parse_kwic_full_context_page

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "kwic_full_context_tel_dan_roman.html"
_SOURCE_URL = "https://cal.huc.edu/get_a_kwicchapter.php?file=13250&sub=&cset=R&target=1325003"
_RETRIEVED_AT = datetime(2026, 9, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    "replacement",
    [
        "",
        "&amp;hasvariant=x",
        "&amp;hasvariant=0&amp;hasvariant=1",
        "&amp;hasvariant=0&amp;unexpected=1",
    ],
)
def test_full_context_lexical_link_query_shape_fails_closed(replacement: str) -> None:
    body = FIXTURE.read_text().replace("&amp;hasvariant=0", replacement, 1)
    response = CalResponse(
        status_code=200,
        url=_SOURCE_URL,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )

    with pytest.raises(ConcordanceParseError):
        parse_kwic_full_context_page(
            response,
            requested_file_id="13250",
            requested_subtext_id=None,
            requested_target_coordinate="1325003",
            requested_charset="R",
        )


def test_comment_identified_context_row_without_lexical_links_fails_closed() -> None:
    body = FIXTURE.read_text().replace(
        "getlex.php?coord=1325002",
        "brokenlex.php?coord=1325002",
    )
    response = CalResponse(
        status_code=200,
        url=_SOURCE_URL,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )

    with pytest.raises(ConcordanceParseError):
        parse_kwic_full_context_page(
            response,
            requested_file_id="13250",
            requested_subtext_id=None,
            requested_target_coordinate="1325003",
            requested_charset="R",
        )
