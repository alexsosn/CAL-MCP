from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageStatus, TextService

GINZA_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_page_ginza_right_001.html"


def _direct_body() -> bytes:
    body = GINZA_FIXTURE.read_bytes().replace(
        b'<a href="get_a_chapter.php?cset=M&amp;file=74410&amp;sub=002">next page</a>\n',
        b"",
    )
    return body.replace(b"74410", b"74501")


class DirectMandaicTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request == CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74501")),
        )
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/get_a_chapter.php?cset=M&file=74501",
            body=_direct_body(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
        )


@pytest.mark.anyio
async def test_direct_mandaic_page_one_uses_ordinary_unpaginated_parser_mode() -> None:
    transport = DirectMandaicTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74501", page=1)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.page == 1
    assert result.page.page_count is None
    assert result.page.total_lines is None
    assert result.page.previous_page is None
    assert result.page.next_page is None
    assert result.provenance.upstream_id == "74501"
    assert result.provenance.page == 1
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74501")),
        )
    ]
