from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageStatus, TextParseError, TextService, parse_text_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
LEGACY_FIXTURE = FIXTURES / "text_page_ginza_right_001.html"
CURRENT_FIXTURE = FIXTURES / "text_page_ginza_right_001_current.html"
CURRENT_PAGE_2 = FIXTURES / "text_page_mandaic_74401_12_p2_current.html"


def _legacy_response(body: bytes | None = None, *, sub: str = "001") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/get_a_chapter.php?cset=M&file=74410&sub={sub}",
        body=LEGACY_FIXTURE.read_bytes() if body is None else body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
    )


def _current_page_one_without_cross_sub_navigation() -> bytes:
    body = CURRENT_FIXTURE.read_bytes()
    start = body.index(b'<a href="get_a_chapter.php?file=74410&sub=002')
    end = body.index(b"</a>", start) + len(b"</a>")
    return body[:start] + body[end:]


def test_mandaic_getlex_links_are_preserved_as_text_tokens() -> None:
    body = LEGACY_FIXTURE.read_bytes().replace(
        b'<a href="get_a_chapter.php?cset=M&amp;file=74410&amp;sub=002">next page</a>',
        b"",
    )

    page = parse_text_page(
        _legacy_response(body),
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
    assert first.tokens[0].lexical_url == "https://cal.huc.edu/getlex.php?coord=7441000101&word=0"


class PageOneTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request == CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74410"), ("sub", "001")),
        )
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/get_a_chapter.php?cset=M&file=74410&sub=001",
            body=_current_page_one_without_cross_sub_navigation(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


@pytest.mark.anyio
async def test_ginza_right_selected_subtext_page_one_uses_one_specialized_request() -> None:
    transport = PageOneTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74410", subtext_id="001", page=1)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.subtext_id == "001"
    assert result.page.page == 1
    assert result.page.page_count is None
    assert result.page.previous_page is None
    assert result.page.next_page is None
    assert result.page.lines[0].display_coordinate == "001:01"
    assert result.provenance.subtext_id == "001"
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74410"), ("sub", "001")),
        )
    ]


class StopAfterRequest(Exception):
    pass


class StopTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        raise StopAfterRequest


@pytest.mark.anyio
async def test_large_mandaic_page_number_is_not_truncated_or_reused_as_subtext() -> None:
    transport = StopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(StopAfterRequest):
            await TextService(client).page("74410", subtext_id="001", page=1000)
    finally:
        await client.aclose()

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(
                ("cset", "M"),
                ("file", "74410"),
                ("sub", "001"),
                ("page", "999"),
            ),
        )
    ]


@pytest.mark.anyio
async def test_explicit_mandaic_subtext_keeps_cset_and_independent_page_route() -> None:
    transport = StopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(StopAfterRequest):
            await TextService(client).page("74410", subtext_id="17", page=2)
    finally:
        await client.aclose()

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74410"), ("sub", "17"), ("page", "1")),
        )
    ]


class MutatedCurrentNavigationTransport:
    def __init__(self, old: bytes, new: bytes) -> None:
        self.old = old
        self.new = new

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert request == CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("cset", "M"), ("file", "74401"), ("sub", "12"), ("page", "1")),
        )
        body = CURRENT_PAGE_2.read_bytes()
        assert self.old in body
        body = body.replace(self.old, self.new, 1)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/get_a_chapter.php?cset=M&file=74401&sub=12&page=1",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (b"cset=M", b"cset=X", "navigation cset"),
        (b"file=74401", b"file=74402", "navigation file"),
        (b"sub=12", b"sub=13", "navigation subtext"),
        (b"page=2&clen=5", b"page=3&clen=5", "next-page"),
    ],
)
async def test_current_mandaic_navigation_mismatch_fails_closed(
    old: bytes,
    new: bytes,
    message: str,
) -> None:
    client = CalHttpClient(transport=MutatedCurrentNavigationTransport(old, new))
    try:
        with pytest.raises(TextParseError, match=message):
            await TextService(client).page("74401", subtext_id="12", page=2)
    finally:
        await client.aclose()
