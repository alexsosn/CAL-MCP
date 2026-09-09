from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextCataloguePage, TextParseError, TextService, parse_text_catalogue_page

_RETRIEVED_AT = datetime(2026, 9, 9, 20, 0, tzinfo=UTC)
_ROOT_URL = "https://cal.huc.edu/newtextmenu.html"
_MANDAIC_URL = "https://cal.huc.edu/show_Mandaic.php?R1=74"


def _response(body: str, url: str = _ROOT_URL) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _mandaic_parser() -> Callable[[CalResponse], TextCataloguePage]:
    module = importlib.import_module("cal_mcp.texts")
    parser = getattr(module, "parse_mandaic_catalogue_page", None)
    assert callable(parser), "texts.parse_mandaic_catalogue_page must exist"
    return cast(Callable[[CalResponse], TextCataloguePage], parser)


def test_root_catalogue_preserves_mandaic_branch_in_cal_order() -> None:
    page = parse_text_catalogue_page(
        _response(
            "<html><body>"
            '<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
            '<a href="targum_onkelos_jonathan.html">'
            "Targums Onkelos and Jonathan to the Prophets"
            "</a>"
            '<a href="show_Mandaic.php?R1=74">Mandaic</a>'
            "</body></html>"
        )
    )

    assert [(item.category_id, item.label) for item in page.categories] == [
        ("3", "Biblical Aramaic"),
        ("51", "Targums Onkelos and Jonathan to the Prophets"),
        ("74", "Mandaic"),
    ]


def test_exact_mandaic_root_route_preserves_changed_nonempty_label() -> None:
    page = parse_text_catalogue_page(
        _response('<a href="show_Mandaic.php?R1=74">Mandaean texts</a>')
    )

    assert [(item.category_id, item.label) for item in page.categories] == [
        ("74", "Mandaean texts")
    ]


@pytest.mark.parametrize(
    "href",
    [
        "changed_mandaic.php?R1=74",
        "show_Mandaic.php",
        "show_Mandaic.php?R1=75",
        "show_Mandaic.php?R1=74&R1=75",
        "show_Mandaic.php?R1=74&cset=M",
        "legacy/show_Mandaic.php?R1=74",
        "https://example.org/show_Mandaic.php?R1=74",
    ],
)
def test_mandaic_labelled_changed_root_route_fails_closed(href: str) -> None:
    response = _response(
        "<html><body>"
        '<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
        f'<a href="{href}">Mandaic</a>'
        "</body></html>"
    )

    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)


def test_dedicated_mandaic_catalogue_returns_subdivided_and_direct_rows_as_texts() -> None:
    page = _mandaic_parser()(
        _response(
            "<html><body>"
            '<p><a href="showsubtexts.php?cset=M&amp;subtext=74401">74401</a> '
            "ATS (The Thousand and Twelve Questions)</p>"
            '<p><a href="get_a_chapter.php?cset=M&amp;file=74501">74501</a> '
            "Haran Gauaita</p>"
            "</body></html>",
            _MANDAIC_URL,
        )
    )

    assert page.categories == ()
    assert [(item.file_id, item.subtext_id, item.label) for item in page.texts] == [
        ("74401", None, "ATS (The Thousand and Twelve Questions)"),
        ("74501", None, "Haran Gauaita"),
    ]


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_category_74_dispatches_to_dedicated_mandaic_catalogue_once() -> None:
    transport = RecordingTransport(
        _response(
            '<p><a href="get_a_chapter.php?cset=M&amp;file=74501">74501</a> Haran Gauaita</p>',
            _MANDAIC_URL,
        )
    )
    service = TextService(CalHttpClient(transport=transport))

    result = await service.catalogue(category_id="74")

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="show_Mandaic.php",
            params=(("R1", "74"),),
        )
    ]
    assert result.provenance.category_id == "74"
    assert [(item.file_id, item.label) for item in result.texts] == [("74501", "Haran Gauaita")]


@pytest.mark.parametrize(
    "url",
    [
        "https://cal.huc.edu/showsubtexts.php?R1=74",
        "https://cal.huc.edu/show_Mandaic.php",
        "https://cal.huc.edu/show_Mandaic.php?R1=75",
        "https://cal.huc.edu/show_Mandaic.php?R1=74&R1=75",
        "https://cal.huc.edu/show_Mandaic.php?R1=74&cset=M",
    ],
)
def test_dedicated_mandaic_catalogue_rejects_response_identity_drift(url: str) -> None:
    response = _response(
        '<a href="get_a_chapter.php?cset=M&amp;file=74501">74501</a> Haran Gauaita',
        url,
    )

    with pytest.raises(TextParseError):
        _mandaic_parser()(response)


@pytest.mark.parametrize(
    "href",
    [
        "showsubtexts.php?subtext=74401",
        "showsubtexts.php?cset=H&subtext=74401",
        "showsubtexts.php?cset=M&subtext=74401&extra=1",
        "showsubtexts.php?cset=M&subtext=74401&subtext=74402",
        "showsubtexts.php?cset=M&subtext=0",
        "showsubtexts.php?cset=M&subtext=abc",
        "get_a_chapter.php?file=74501",
        "get_a_chapter.php?cset=H&file=74501",
        "get_a_chapter.php?cset=M&file=74501&extra=1",
        "get_a_chapter.php?cset=M&file=74501&file=74502",
        "get_a_chapter.php?cset=M&file=0",
        "get_a_chapter.php?cset=M&file=abc",
        "https://example.org/get_a_chapter.php?cset=M&file=74501",
        "https://example.org/showsubtexts.php?cset=M&subtext=74401",
    ],
)
def test_dedicated_mandaic_catalogue_rejects_malformed_recognized_child_route(
    href: str,
) -> None:
    response = _response(
        f'<p><a href="{href}">74501</a> malformed</p>',
        _MANDAIC_URL,
    )

    with pytest.raises(TextParseError):
        _mandaic_parser()(response)


def test_dedicated_mandaic_catalogue_rejects_duplicate_file_ids_across_route_families() -> None:
    response = _response(
        "<html><body>"
        '<p><a href="showsubtexts.php?cset=M&amp;subtext=74501">74501</a> first</p>'
        '<p><a href="get_a_chapter.php?cset=M&amp;file=74501">74501</a> second</p>'
        "</body></html>",
        _MANDAIC_URL,
    )

    with pytest.raises(TextParseError):
        _mandaic_parser()(response)


def test_dedicated_mandaic_catalogue_rejects_ambiguous_row() -> None:
    response = _response(
        '<p><a href="showsubtexts.php?cset=M&amp;subtext=74401">74401</a> '
        '<a href="get_a_chapter.php?cset=M&amp;file=74501">74501</a> ambiguous</p>',
        _MANDAIC_URL,
    )

    with pytest.raises(TextParseError):
        _mandaic_parser()(response)


@pytest.mark.parametrize(
    "body",
    [
        "<h1>Mandaic</h1><p>No recognizable rows</p>",
        '<p><a href="get_a_chapter.php?cset=M&amp;file=74501">74501</a></p>',
        '<p>detached <a href="get_a_chapter.php?cset=M&amp;file=74501"></a></p>',
    ],
)
def test_dedicated_mandaic_catalogue_fails_closed_without_usable_rendered_rows(body: str) -> None:
    with pytest.raises(TextParseError):
        _mandaic_parser()(_response(body, _MANDAIC_URL))
