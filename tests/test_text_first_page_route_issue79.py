from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageStatus, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


class FirstPageTransport:
    def __init__(self, fixture_name: str, source_url: str) -> None:
        self.fixture_name = fixture_name
        self.source_url = source_url
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return CalResponse(
            status_code=200,
            url=self.source_url,
            body=(FIXTURES / self.fixture_name).read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("file_id", "fixture_name", "source_url", "expected_page_count"),
    [
        (
            "13250",
            "text_page_tel_dan.html",
            "https://cal.huc.edu/get_a_chapter.php?file=13250",
            None,
        ),
        (
            "71026",
            "text_page_bt_az.html",
            "https://cal.huc.edu/get_a_chapter.php?file=71026",
            50,
        ),
    ],
)
async def test_public_first_page_uses_cal_default_route_without_page_zero(
    file_id: str,
    fixture_name: str,
    source_url: str,
    expected_page_count: int | None,
) -> None:
    transport = FirstPageTransport(fixture_name, source_url)
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page(file_id, page=1)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.page == 1
    assert result.page.page_count == expected_page_count
    assert result.provenance.upstream_id == file_id
    assert result.provenance.page == 1
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("file", file_id),),
        )
    ]
