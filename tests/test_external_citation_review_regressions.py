from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.external_citations import (
    ExternalCitationParseError,
    parse_external_citation_sources_page,
)


def _source_response(abbreviation: str) -> CalResponse:
    body = (
        "<html><body><h1>Texts With Citations, No Full Text Yet</h1>"
        '<div class="cit-row"><a class="cit-abbrev" '
        f'href="/displaycits.abbrev.php?abbrev={abbreviation}">{abbreviation}</a>'
        "</div></body></html>"
    )
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/display.notext.abbrevs.php?dial=6&dial1=6",
        body=body.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, 19, 50, tzinfo=UTC),
    )


def test_returned_source_format_control_fails_closed() -> None:
    with pytest.raises(ExternalCitationParseError):
        parse_external_citation_sources_page(_source_response("A\u200dB"))


def test_returned_source_abbreviation_over_public_limit_fails_closed() -> None:
    with pytest.raises(ExternalCitationParseError):
        parse_external_citation_sources_page(_source_response("A" * 129))
