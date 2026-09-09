from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 9, tzinfo=UTC)


class CoexistenceTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.path == "targum_onkelos_jonathan.html":
            return CalResponse(
                status_code=200,
                url="https://cal.huc.edu/targum_onkelos_jonathan.html",
                body=b'<html><body><a href="get_a_chapter.php?file=51400">MegTan</a></body></html>',
                content_type="text/html; charset=UTF-8",
                retrieved_at=RETRIEVED_AT,
            )
        if request.path == "get_a_chapter.php":
            return CalResponse(
                status_code=200,
                url="https://cal.huc.edu/get_a_chapter.php?cset=M&file=74717",
                body=(FIXTURES / "text_page_mandaic_direct_74717.html").read_bytes(),
                content_type="text/html; charset=UTF-8",
                retrieved_at=RETRIEVED_AT,
            )
        raise AssertionError(f"unexpected CAL path: {request.path}")


@pytest.mark.anyio
async def test_onkelos_catalogue_and_direct_mandaic_page_routes_coexist() -> None:
    transport = CoexistenceTransport()
    service = TextService(CalHttpClient(transport=transport))

    await service.catalogue(category_id="51")
    await service.page("74717", page=1)

    assert transport.requests == [
        CalRequest(method="GET", path="targum_onkelos_jonathan.html"),
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74717")),
        ),
    ]
