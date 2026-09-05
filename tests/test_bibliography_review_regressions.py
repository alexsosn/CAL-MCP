from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.bibliography import (
    BibliographyParseError,
    BibliographyService,
    parse_bibliography_page,
)
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse


def _response(body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getbibsigla.php?myauthor=TADA",
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_result_heading_must_match_submitted_query() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return _response(
            b"<html><body><h1>CAL Bibliography for JBA</h1>"
            b'<div class="card">A structurally valid record.</div></body></html>'
        )

    service = BibliographyService(CalHttpClient(transport=transport))

    with pytest.raises(BibliographyParseError):
        await service.keyword("TADA")

    assert requests == [
        CalRequest(
            method="GET",
            path="getbibsigla.php",
            params=(("myauthor", "TADA"),),
        )
    ]


def test_no_data_marker_must_match_result_heading() -> None:
    response = _response(
        b"<html><body><h1>CAL Bibliography for TADA</h1>"
        b"<p>NO data FOR JBA ARE CURRENTLY STORED</p></body></html>"
    )

    with pytest.raises(BibliographyParseError):
        parse_bibliography_page(response)
