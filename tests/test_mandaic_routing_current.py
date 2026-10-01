"""Issue #188: current Mandaic subtext/page routing.

See docs/research/issue-188-mandaic-routing.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalInputError
from cal_mcp.texts import TextPageStatus, TextParseError, TextService, parse_text_catalogue_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(body: bytes, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
    )


class ChildCatalogueTransport:
    def __init__(self, file_id: str, body: bytes) -> None:
        self.file_id = file_id
        self.body = body
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request == CalRequest(
            method="GET",
            path="showsubtexts.php",
            params=(("subtext", self.file_id),),
        )
        return _response(
            self.body,
            f"https://cal.huc.edu/showsubtexts.php?subtext={self.file_id}",
        )


async def _child_catalogue(file_id: str, body: bytes):
    transport = ChildCatalogueTransport(file_id, body)
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).catalogue(category_id=file_id)
    finally:
        await client.aclose()
    return result, transport.requests


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("file_id", "fixture", "expected"),
    [
        (
            "74401",
            "text_catalogue_mandaic_74401_children_current.html",
            [("74401", "11"), ("74401", "12"), ("74401", "23")],
        ),
        (
            "74430",
            "text_catalogue_mandaic_74430_children_current.html",
            [("74430", "1"), ("74430", "2"), ("74430", "3")],
        ),
        (
            "74421",
            "text_catalogue_mandaic_74421_children_current.html",
            [("74421", "000"), ("74421", "103"), ("74421", "col")],
        ),
    ],
)
async def test_mandaic_child_catalogue_preserves_exact_subtext_ids(
    file_id: str,
    fixture: str,
    expected: list[tuple[str, str]],
) -> None:
    result, requests = await _child_catalogue(file_id, (FIXTURES / fixture).read_bytes())

    assert result.categories == ()
    assert [(item.file_id, item.subtext_id) for item in result.texts] == expected
    assert requests == [
        CalRequest(
            method="GET",
            path="showsubtexts.php",
            params=(("subtext", file_id),),
        )
    ]


@pytest.mark.anyio
async def test_mandaic_child_catalogue_rejects_wrong_script_selector() -> None:
    body = (FIXTURES / "text_catalogue_mandaic_74430_children_current.html").read_bytes()
    body = body.replace(b"sub=1&cset=J", b"sub=1&cset=X", 1)

    with pytest.raises(TextParseError, match="cset|script"):
        await _child_catalogue("74430", body)


@pytest.mark.anyio
async def test_mandaic_child_catalogue_rejects_wrong_info_coordinate() -> None:
    body = (FIXTURES / "text_catalogue_mandaic_74430_children_current.html").read_bytes()
    body = body.replace(b"coord=744301", b"coord=744399", 1)

    with pytest.raises(TextParseError, match="information|coordinate"):
        await _child_catalogue("74430", body)


def test_non_mandaic_subtext_grammar_still_rejects_col() -> None:
    response = _response(
        b'<a href="/get_a_chapter.php?file=55000&sub=col&cset=C">bad</a>',
        "https://cal.huc.edu/showsubtexts.php?subtext=55000",
    )
    with pytest.raises(TextParseError, match="subtext"):
        parse_text_catalogue_page(response)


class StopAfterRequest(Exception):
    pass


class RecordingStopTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        raise StopAfterRequest


@pytest.mark.anyio
async def test_known_subdivided_mandaic_requires_explicit_subtext() -> None:
    transport = RecordingStopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(CalInputError, match="subtext"):
            await TextService(client).page("74401", page=1)
    finally:
        await client.aclose()

    assert transport.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("file_id", "subtext_id", "page", "expected_params"),
    [
        (
            "74401",
            "12",
            1,
            (("cset", "M"), ("file", "74401"), ("sub", "12")),
        ),
        (
            "74430",
            "1",
            1,
            (("cset", "M"), ("file", "74430"), ("sub", "1")),
        ),
        (
            "74421",
            "col",
            1,
            (("cset", "M"), ("file", "74421"), ("sub", "col")),
        ),
        (
            "74401",
            "12",
            2,
            (("cset", "M"), ("file", "74401"), ("sub", "12"), ("page", "1")),
        ),
        (
            "74501",
            None,
            2,
            (("cset", "M"), ("file", "74501"), ("page", "1")),
        ),
    ],
)
async def test_current_mandaic_request_uses_subtext_and_page_as_separate_axes(
    file_id: str,
    subtext_id: str | None,
    page: int,
    expected_params: tuple[tuple[str, str], ...],
) -> None:
    transport = RecordingStopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(StopAfterRequest):
            await TextService(client).page(file_id, subtext_id=subtext_id, page=page)
    finally:
        await client.aclose()

    assert transport.requests == [
        CalRequest(method="GET", path="get_a_chapter.php", params=expected_params)
    ]


@pytest.mark.anyio
async def test_legacy_direct_mandaic_is_still_page_one_only() -> None:
    transport = RecordingStopTransport()
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(CalInputError, match="page 1"):
            await TextService(client).page("74717", page=2)
    finally:
        await client.aclose()
    assert transport.requests == []


class CurrentPageTransport:
    def __init__(self, expected: CalRequest, fixture: str, url: str) -> None:
        self.expected = expected
        self.fixture = fixture
        self.url = url
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request == self.expected
        return _response((FIXTURES / self.fixture).read_bytes(), self.url)


@pytest.mark.anyio
async def test_current_subdivided_mandaic_page_two_uses_real_page_axis() -> None:
    expected = CalRequest(
        method="GET",
        path="get_a_chapter.php",
        params=(("cset", "M"), ("file", "74401"), ("sub", "12"), ("page", "1")),
    )
    transport = CurrentPageTransport(
        expected,
        "text_page_mandaic_74401_12_p2_current.html",
        "https://cal.huc.edu/get_a_chapter.php?cset=M&file=74401&sub=12&page=1",
    )
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74401", subtext_id="12", page=2)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.file_id == "74401"
    assert result.page.text.subtext_id == "12"
    assert (result.page.page, result.page.page_count, result.page.total_lines) == (2, 20, 468)
    assert (result.page.previous_page, result.page.next_page) == (1, 3)
    assert transport.requests == [expected]


@pytest.mark.anyio
async def test_current_direct_mandaic_page_two_is_paginated_without_subtext() -> None:
    expected = CalRequest(
        method="GET",
        path="get_a_chapter.php",
        params=(("cset", "M"), ("file", "74501"), ("page", "1")),
    )
    transport = CurrentPageTransport(
        expected,
        "text_page_mandaic_direct_74501_p2_current.html",
        "https://cal.huc.edu/get_a_chapter.php?cset=M&file=74501&page=1",
    )
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).page("74501", page=2)
    finally:
        await client.aclose()

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.subtext_id is None
    assert (result.page.page, result.page.page_count, result.page.total_lines) == (2, 11, 246)
    assert (result.page.previous_page, result.page.next_page) == (1, 3)
    assert transport.requests == [expected]
