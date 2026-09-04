from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import (
    TextParseError,
    TextService,
    parse_text_catalogue_page,
    parse_text_page,
    parse_text_search_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )


def test_text_search_preserves_cal_text_identifier_and_description() -> None:
    page = parse_text_search_page(
        _fixture_response("text_search_tel_dan.html", "https://cal.huc.edu/newsearchtxts.php")
    )

    assert len(page.matches) == 1
    match = page.matches[0]
    assert match.file_id == "13250"
    assert match.subtext_id is None
    assert match.label == "TDanStel (Tel Dan Stele)"
    assert match.description == (
        "Line 2 Text according to A. Biran and J. Naveh; dated to 9th century"
    )


def test_recognizable_empty_text_search_is_not_parser_drift() -> None:
    page = parse_text_search_page(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/newsearchtxts.php",
            body=(
                b"<html><body><div>CAL search for texts like: no-such-text. "
                b"Click on the file number to view.</div></body></html>"
            ),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        )
    )
    assert page.matches == ()


def test_text_catalogue_is_bounded_and_keeps_subtext_navigation_explicit() -> None:
    root = parse_text_catalogue_page(
        _fixture_response("text_catalogue_root.html", "https://cal.huc.edu/newtextmenu.html")
    )
    assert [(item.category_id, item.label) for item in root.categories] == [
        ("3", "Biblical Aramaic"),
        ("21", "Qumran"),
    ]
    assert [(item.file_id, item.subtext_id, item.label) for item in root.texts] == [
        ("13250", None, "Tel Dan Stele")
    ]

    biblical = parse_text_catalogue_page(
        _fixture_response(
            "text_catalogue_biblical.html",
            "https://cal.huc.edu/showsubtexts.php?subtext=3",
        )
    )
    assert biblical.categories == ()
    assert [(item.file_id, item.subtext_id, item.label) for item in biblical.texts] == [
        ("30000", "1", "chapter 1"),
        ("30000", "2", "chapter 2"),
        ("31000", "4", "BA Ezra chapter 4"),
    ]


def test_text_page_preserves_page_metadata_coordinates_and_token_positions() -> None:
    page = parse_text_page(
        _fixture_response(
            "text_page_bt_az.html",
            "https://cal.huc.edu/get_a_chapter.php?file=71026&page=0",
        ),
        requested_file_id="71026",
        requested_subtext_id=None,
    )

    assert page.text.file_id == "71026"
    assert page.text.label == "BT AZ"
    assert page.page == 1
    assert page.page_count == 50
    assert page.total_lines == 2413
    assert page.previous_page is None
    assert page.next_page == 2
    assert len(page.lines) == 2

    first = page.lines[0]
    assert first.coordinate == "7102601002107"
    assert first.display_coordinate == "ms01 pg002 sd1 ln07"
    assert first.comment_url is None
    assert [(token.word_index, token.text) for token in first.tokens] == [
        (0, "xd"),
        (1, "t)ny"),
    ]

    second = page.lines[1]
    assert second.coordinate == "7102601002203"
    assert second.display_coordinate == "ms01 pg002 sd2 ln03"
    assert second.comment_url == "https://cal.huc.edu/comment.php?coord=7102601002203"
    assert [(token.word_index, token.text) for token in second.tokens] == [
        (0, "m)N"),
        (1, "dtny"),
    ]


def test_text_parsers_fail_explicitly_on_unrecognized_success_pages() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/unknown",
        body=b"<html><body>changed upstream markup</body></html>",
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )
    with pytest.raises(TextParseError):
        parse_text_search_page(response)
    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)
    with pytest.raises(TextParseError):
        parse_text_page(response, requested_file_id="71026", requested_subtext_id=None)


class RecordingTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.path == "newsearchtxts.php":
            return _fixture_response(
                "text_search_tel_dan.html",
                "https://cal.huc.edu/newsearchtxts.php",
            )
        if request.path == "newtextmenu.html":
            return _fixture_response(
                "text_catalogue_root.html",
                "https://cal.huc.edu/newtextmenu.html",
            )
        if request.path == "showsubtexts.php":
            return _fixture_response(
                "text_catalogue_biblical.html",
                "https://cal.huc.edu/showsubtexts.php?subtext=3",
            )
        if request.path == "get_a_chapter.php":
            return _fixture_response(
                "text_page_bt_az.html",
                "https://cal.huc.edu/get_a_chapter.php?file=71026&page=0",
            )
        raise AssertionError(f"unexpected request: {request}")


@pytest.mark.anyio
async def test_text_service_uses_one_request_per_explicit_operation() -> None:
    transport = RecordingTransport()
    service = TextService(CalHttpClient(transport=transport))

    search = await service.search(" Tel   Dan ")
    root = await service.catalogue()
    category = await service.catalogue(category_id="3")
    page = await service.page("71026", page=1)

    assert search.provenance.original_query == " Tel   Dan "
    assert search.provenance.submitted_query == "Tel Dan"
    assert len(root.texts) == 1
    assert len(category.texts) == 3
    assert page.page.page == 1

    requests = [
        (request.method, request.path, request.params, request.data)
        for request in transport.requests
    ]
    assert requests == [
        ("POST", "newsearchtxts.php", (), (("search", "Tel Dan"),)),
        ("GET", "newtextmenu.html", (), ()),
        ("GET", "showsubtexts.php", (("subtext", "3"),), ()),
        ("GET", "get_a_chapter.php", (("file", "71026"), ("page", "0")), ()),
    ]


@pytest.mark.anyio
async def test_text_page_maps_public_page_two_to_upstream_page_one() -> None:
    transport = RecordingTransport()
    service = TextService(CalHttpClient(transport=transport))

    await service.page("71026", subtext_id="4", page=2)

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="get_a_chapter.php",
            params=(("file", "71026"), ("sub", "4"), ("page", "1")),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "args"),
    [
        ("search", ("   ",)),
        ("catalogue", ("../3",)),
        ("page", ("abc",)),
        ("page_zero", ("71026",)),
        ("page_subtext", ("71026",)),
    ],
)
async def test_invalid_text_requests_fail_before_transport(
    operation: str,
    args: tuple[str, ...],
) -> None:
    transport = RecordingTransport()
    service = TextService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        if operation == "search":
            await service.search(*args)
        elif operation == "catalogue":
            await service.catalogue(category_id=args[0])
        elif operation == "page_zero":
            await service.page(args[0], page=0)
        elif operation == "page_subtext":
            await service.page(args[0], subtext_id="x", page=1)
        else:
            await service.page(*args)

    assert transport.requests == []
