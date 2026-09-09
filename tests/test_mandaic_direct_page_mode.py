from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageStatus, TextService

DIRECT_FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_page_mandaic_direct_74717.html"


class DirectMandaicTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request == CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74717")),
        )
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/get_a_chapter.php?cset=M&file=74717",
            body=DIRECT_FIXTURE.read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
        )


@pytest.mark.anyio
async def test_direct_mandaic_page_one_uses_observed_unpaginated_parser_mode() -> None:
    transport = DirectMandaicTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74717", page=1)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.file_id == "74717"
    assert result.page.text.label == "Qmaha Dbr ˁngaria"
    assert result.page.page == 1
    assert result.page.page_count is None
    assert result.page.total_lines is None
    assert result.page.previous_page is None
    assert result.page.next_page is None
    assert len(result.page.lines) == 1
    assert result.page.lines[0].coordinate == "74717001"
    assert result.page.lines[0].display_coordinate == "001"
    assert [(token.word_index, token.text) for token in result.page.lines[0].tokens] == [
        (0, "bšumaihun")
    ]
    assert result.provenance.upstream_id == "74717"
    assert result.provenance.page == 1
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74717")),
        )
    ]
