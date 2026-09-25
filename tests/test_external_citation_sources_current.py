"""Issue #153: CAL lists some source abbreviations more than once.

See docs/research/issue-153-external-sources-repeated-abbreviations.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalResponse
from cal_mcp.external_citations import (
    ExternalCitationParseError,
    ExternalCitationSourcePage,
    parse_external_citation_sources_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
URL = "https://cal.huc.edu/display.notext.abbrevs.php?dial1=6&dial=6"


def _parse(body: str) -> ExternalCitationSourcePage:
    return parse_external_citation_sources_page(
        CalResponse(
            status_code=200,
            url=URL,
            body=body.encode(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 24, tzinfo=UTC),
        )
    )


def _body() -> str:
    return (FIXTURES / "external_citation_sources_syriac_current.html").read_text(encoding="utf-8")


def test_repeated_abbreviations_are_kept_in_cal_order_with_distinct_descriptions() -> None:
    page = _parse(_body())

    assert [source.abbreviation for source in page.sources] == [
        "1CorH",
        "EbPar",
        "EbPar",
        "JS",
        "JS",
    ]
    ebpar = [source for source in page.sources if source.abbreviation == "EbPar"]
    assert (ebpar[0].description or "").startswith("E. Gismondi")
    assert (ebpar[1].description or "").startswith("P. Cardahi")
    assert {source.citations_url for source in ebpar} == {
        "https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar"
    }


def test_repeated_abbreviation_cannot_point_to_a_different_citation_list() -> None:
    # The link must carry exactly the displayed abbreviation, so a repeated abbreviation
    # can never be routed to another source's citations.
    body = _body()
    second = body.rindex('href="displaycits.abbrev.php?abbrev=EbPar"')
    body = (
        body[:second]
        + 'href="displaycits.abbrev.php?abbrev=EbPar2"'
        + body[second + len('href="displaycits.abbrev.php?abbrev=EbPar"') :]
    )
    with pytest.raises(ExternalCitationParseError, match="does not match its abbreviation"):
        _parse(body)
