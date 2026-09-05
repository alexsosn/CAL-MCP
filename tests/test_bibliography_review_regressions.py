from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.bibliography import BibliographyParseError, BibliographyService
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse


@pytest.mark.anyio
async def test_result_heading_must_match_submitted_query() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/getbibsigla.php?myauthor=TADA",
            body=(
                b"<html><body><h1>CAL Bibliography for JBA</h1>"
                b'<div class="card">A structurally valid record.</div></body></html>'
            ),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
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
