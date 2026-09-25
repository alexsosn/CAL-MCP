"""Issue #166: current (2026-09-25) file-info coordinate on subdivided text pages.

See docs/research/issue-166-subtext-file-info.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import (
    TextPageResult,
    TextPageStatus,
    TextParseError,
    TextService,
    parse_text_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
SAMARITAN = FIXTURES / "text_page_samaritan_56000_112_current.html"
GINZA = FIXTURES / "text_page_ginza_right_001_current.html"


class FixtureTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        query = "&".join(f"{name}={value}" for name, value in request.params)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/get_a_chapter.php?{query}",
            body=self.body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


async def _page(body: bytes, file_id: str, subtext_id: str | None = None) -> TextPageResult:
    client = CalHttpClient(transport=FixtureTransport(body))
    try:
        return await TextService(client).page(file_id, subtext_id=subtext_id)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_current_ordinary_subtext_page_is_read() -> None:
    result = await _page(SAMARITAN.read_bytes(), "56000", "112")

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.file_id == "56000"
    assert result.page.text.subtext_id == "112"
    assert result.page.text.label == "SamTgJ Gen chapter 12"
    assert [line.coordinate for line in result.page.lines] == ["56000112010", "56000112020"]
    assert result.page.lines[0].tokens[0].text == "w)mr"


@pytest.mark.anyio
async def test_current_mandaic_subdivided_page_is_read() -> None:
    result = await _page(GINZA.read_bytes(), "74410")

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.file_id == "74410"
    assert result.page.text.subtext_id is None
    assert result.page.text.label == "Ginza Rabba (Great Treasury) Right Side"
    assert [line.coordinate for line in result.page.lines] == ["7441000101", "7441000102"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "coord",
    [
        "56001112",  # different file
        "56000113",  # different subtext
        "560000112",  # different padding of the subtext
        "5600011",  # truncated subtext
        "56000112x",  # not decimal
    ],
)
async def test_file_info_coord_naming_another_file_or_subtext_fails_closed(coord: str) -> None:
    body = SAMARITAN.read_bytes().replace(b'coord=56000112"', f'coord={coord}"'.encode())
    assert f"coord={coord}".encode() in body
    with pytest.raises(TextParseError):
        await _page(body, "56000", "112")


@pytest.mark.anyio
async def test_file_plus_subtext_coord_is_rejected_without_a_submitted_sub() -> None:
    # A request without ``sub`` must still name the bare file (earlier and current layout).
    body = SAMARITAN.read_bytes().replace(b'coord=56000112"', b'coord=5600011"')
    with pytest.raises(TextParseError, match="file identifier differs"):
        await _page(body, "56000")


@pytest.mark.anyio
async def test_mandaic_file_info_coord_with_another_page_selector_fails_closed() -> None:
    body = GINZA.read_bytes().replace(b'coord=74410001"', b'coord=74410002"')
    with pytest.raises(TextParseError, match="file identifier differs"):
        await _page(body, "74410")


@pytest.mark.anyio
async def test_current_mandaic_page_keeps_its_next_page_navigation() -> None:
    result = await _page(GINZA.read_bytes(), "74410")

    assert result.page is not None
    assert (result.page.previous_page, result.page.next_page) == (None, 2)


def test_public_parser_treats_the_requested_subtext_as_the_submitted_sub() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/get_a_chapter.php?file=56000&sub=112&page=0",
        body=SAMARITAN.read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
    )

    page = parse_text_page(response, requested_file_id="56000", requested_subtext_id="112")

    assert page is not None
    assert page.text.subtext_id == "112"


@pytest.mark.anyio
async def test_prefix_matched_subtext_returns_cal_page_with_each_line_coordinate() -> None:
    # CAL treats ``sub`` as a prefix: ``11`` returns subtexts 112-119 under the first
    # subtext's label. CAL-MCP returns CAL's page as rendered; every line keeps its own
    # CAL coordinate, and the docs tell callers to pass subtext_id exactly as returned.
    body = (FIXTURES / "text_page_samaritan_56000_prefix_11_current.html").read_bytes()
    result = await _page(body, "56000", "11")

    assert result.page is not None
    assert result.page.text.subtext_id == "11"
    assert result.page.text.label == "SamTgJ Gen chapter 12"
    assert [line.coordinate for line in result.page.lines] == ["56000112010", "56000113010"]
