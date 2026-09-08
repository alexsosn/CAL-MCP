from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextParseError, TextService, parse_text_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
    )


class StaticTelDanTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return _fixture_response(
            "text_page_tel_dan_getlex.html",
            "https://cal.huc.edu/get_a_chapter.php?file=13250&page=0",
        )


@pytest.mark.anyio
async def test_text_service_parses_current_tel_dan_getlex_token_links() -> None:
    transport = StaticTelDanTransport()
    service = TextService(CalHttpClient(transport=transport))

    result = await service.page("13250", page=1)

    assert result.status.value == "found"
    assert result.page is not None
    assert result.page.text.file_id == "13250"
    assert result.page.text.subtext_id is None
    assert result.page.text.label == "TDanStel (Tel Dan Stele)"
    assert result.page.page == 1
    assert result.page.page_count is None
    assert result.page.total_lines is None
    assert result.page.previous_page is None
    assert result.page.next_page is None
    assert [
        (line.coordinate, line.display_coordinate, line.text) for line in result.page.lines
    ] == [
        ("1325001", "01", "[,,, ,,,]mr"),
        ("1325002", "02", "[,,, ])by"),
    ]
    assert [
        (token.coordinate, token.word_index, token.text, token.lexical_url)
        for token in result.page.lines[0].tokens
    ] == [
        (
            "1325001",
            0,
            "[,, ,".replace(" ", ""),
            "https://cal.huc.edu/getlex.php?coord=1325001&word=0&hasvariant=0",
        ),
        (
            "1325001",
            1,
            ",,,]mr",
            "https://cal.huc.edu/getlex.php?coord=1325001&word=1&hasvariant=0",
        ),
    ]
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("file", "13250"), ("page", "0")),
        )
    ]


@pytest.mark.parametrize(
    ("href", "message"),
    [
        ("getlex.php?coord=abc&word=0&hasvariant=0", "non-decimal coordinate"),
        ("getlex.php?coord=1325001&word=x&hasvariant=0", "nonnumeric word index"),
    ],
)
def test_malformed_getlex_token_links_fail_closed(href: str, message: str) -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/get_a_chapter.php?file=13250&page=0",
        body=(
            '<html><body><a href="/get_file_info.php?coord=13250">'
            '13250: TDanStel (Tel Dan Stele)</a>'
            f'<div>01 <a href="{href}">token</a></div></body></html>'
        ).encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
    )

    with pytest.raises(TextParseError, match=message):
        parse_text_page(response, requested_file_id="13250", requested_subtext_id=None)
