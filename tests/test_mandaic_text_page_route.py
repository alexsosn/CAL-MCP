from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageStatus, TextService, parse_text_page

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_page_ginza_right_001.html"


def _response(body: bytes | None = None, *, sub: str = "001") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/get_a_chapter.php?cset=M&file=74410&sub={sub}",
        body=FIXTURE.read_bytes() if body is None else body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
    )


def test_mandaic_getlex_links_are_preserved_as_text_tokens() -> None:
    body = FIXTURE.read_bytes().replace(
        b'<a href="get_a_chapter.php?cset=M&amp;file=74410&amp;sub=002">next page</a>',
        b"",
    )

    page = parse_text_page(
        _response(body),
        requested_file_id="74410",
        requested_subtext_id=None,
        requested_page=1,
    )

    assert page is not None
    assert page.text.label == "Ginza Rabba (Great Treasury) Right Side"
    assert [(line.display_coordinate, line.text) for line in page.lines] == [
        ("001:01", "| mšaba marai bliba dakia"),
        ("001:02", "| bšumaihun ḏhiia rbia nukraiia"),
    ]
    first = page.lines[0]
    assert [(token.word_index, token.text) for token in first.tokens] == [
        (0, "mšaba"),
        (1, "marai"),
        (2, "bliba"),
        (3, "dakia"),
    ]
    assert first.tokens[0].coordinate == "7441000101"
    assert first.tokens[0].lexical_url == (
        "https://cal.huc.edu/getlex.php?coord=7441000101&word=0"
    )


class GinzaTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.params == (("cset", "M"), ("file", "74410"), ("sub", "001")):
            return _response()
        if request.params == (("cset", "M"), ("file", "74410"), ("sub", "002")):
            body = FIXTURE.read_bytes().replace(b"sub=002", b"sub=003")
            return _response(body, sub="002")
        raise AssertionError(f"unexpected CAL request: {request}")


@pytest.mark.anyio
async def test_ginza_right_page_one_uses_one_specialized_mandaic_request() -> None:
    transport = GinzaTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74410", page=1)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.page == 1
    assert result.page.page_count is None
    assert result.page.previous_page is None
    assert result.page.next_page == 2
    assert result.page.lines[0].display_coordinate == "001:01"
    assert result.page.lines[0].text == "| mšaba marai bliba dakia"
    assert result.provenance.upstream_id == "74410"
    assert result.provenance.page == 1
    assert len(transport.requests) == 1
    assert transport.requests[0] == CalRequest(
        method="GET",
        path="get_a_chapter.php",
        params=(("cset", "M"), ("file", "74410"), ("sub", "001")),
    )


@pytest.mark.anyio
async def test_mandaic_public_page_two_maps_to_sub_002_without_discovery() -> None:
    transport = GinzaTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74410", page=2)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.page == 2
    assert result.page.page_count is None
    assert result.page.previous_page is None
    assert result.page.next_page == 3
    assert result.provenance.page == 2
    assert len(transport.requests) == 1
    assert transport.requests[0].params == (
        ("cset", "M"),
        ("file", "74410"),
        ("sub", "002"),
    )
