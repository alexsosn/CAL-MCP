from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.search import SearchParseError, parse_citation_search_page


def test_citation_search_rejects_unparsed_extra_content_inside_hit() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/searchcits.php",
        body=(
            b"<html><body>"
            b'<div><a href="oneentry.php?lemma=gml+N&cits=all">gml n.m.</a></div>'
            b"<div>camel</div>"
            b"<div>TAD D.22.1:2 : source text : translation</div>"
            b"<div>unexpected additional semantic content</div>"
            b"</body></html>"
        ),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )

    with pytest.raises(SearchParseError):
        parse_citation_search_page(response)
