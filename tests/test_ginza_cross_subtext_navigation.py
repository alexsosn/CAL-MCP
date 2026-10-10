"""Issue #272: follow Ginza Rabba's CAL page-to-subtext navigation explicitly."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageStatus, TextParseError, TextService

SOURCE = Path(__file__).parent / "fixtures" / "cal" / "text_page_ginza_right_001_current.html"
LINK = b"get_a_chapter.php?file=74410&sub=002&cset=M&clen=5&page=0"
BASE_URL = "https://cal.huc.edu/get_a_chapter.php?cset=M&file=74410&sub=001"
STAMP = datetime(2026, 10, 10, tzinfo=UTC)


class GinzaTransport:
    def __init__(self, body: bytes | None = None) -> None:
        self.body = SOURCE.read_bytes() if body is None else body
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return CalResponse(
            status_code=200,
            url=BASE_URL,
            body=self.body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=STAMP,
        )


@pytest.mark.anyio
async def test_current_ginza_page_has_next_subtext_but_not_next_paginated_page() -> None:
    transport = GinzaTransport()
    client = CalHttpClient(transport=transport)
    result = await TextService(client).page("74410", subtext_id="001", page=1)
    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.file_id == "74410"
    assert result.page.text.subtext_id == "001"
    assert result.page.page == 1
    assert result.page.page_count is None
    assert result.page.total_lines is None
    assert result.page.previous_page is None
    assert result.page.next_page is None
    assert result.page.previous_subtext_id is None
    assert result.page.next_subtext_id == "002"
    assert result.page.lines[0].display_coordinate == "001:01"
    assert result.provenance.subtext_id == "001"
    assert result.to_dict()["page"]["next_subtext_id"] == "002"
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74410"), ("sub", "001")),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "bad_link",
    [
        b"get_a_chapter.php?file=74410&sub=003&cset=M&clen=5&page=0",
        b"get_a_chapter.php?file=74411&sub=002&cset=M&clen=5&page=0",
        b"get_a_chapter.php?file=74410&sub=002&cset=H&clen=5&page=0",
        b"get_a_chapter.php?file=74410&sub=002&cset=M&clen=5&page=1",
        b"get_a_chapter.php?file=74410&sub=002&cset=M&clen=7&page=0",
        b"get_a_chapter.php?file=74410&sub=002&cset=M&clen=5&page=0&extra=1",
        b"https://evil.example/get_a_chapter.php?file=74410&sub=002&cset=M&clen=5&page=0",
    ],
)
async def test_ginza_cross_subtext_link_must_remain_safe_and_adjacent(
    bad_link: bytes,
) -> None:
    body = SOURCE.read_bytes()
    assert body.count(LINK) == 1
    transport = GinzaTransport(body.replace(LINK, bad_link))
    client = CalHttpClient(transport=transport)
    with pytest.raises(TextParseError):
        await TextService(client).page("74410", subtext_id="001", page=1)
    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_ginza_wrong_cross_subtext_navigation_direction_is_drift() -> None:
    body = SOURCE.read_bytes().replace(b">next page</a>", b">previous page</a>")
    transport = GinzaTransport(body)
    with pytest.raises(TextParseError):
        await TextService(CalHttpClient(transport=transport)).page(
            "74410", subtext_id="001", page=1
        )
    assert len(transport.requests) == 1


@pytest.mark.anyio
async def test_ginza_duplicate_cross_subtext_links_are_drift() -> None:
    body = SOURCE.read_bytes()
    body = body.replace(b"</body>", b'<a href="' + LINK + b'">next page</a></body>')
    transport = GinzaTransport(body)
    with pytest.raises(TextParseError):
        await TextService(CalHttpClient(transport=transport)).page(
            "74410", subtext_id="001", page=1
        )
    assert len(transport.requests) == 1
