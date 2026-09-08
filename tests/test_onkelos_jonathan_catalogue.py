from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextParseError, TextService, parse_text_catalogue_page

_RETRIEVED_AT = datetime(2026, 9, 8, tzinfo=UTC)


def _response(body: bytes, url: str = "https://cal.huc.edu/newtextmenu.html") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def test_root_catalogue_preserves_onkelos_jonathan_collection_in_order() -> None:
    page = parse_text_catalogue_page(
        _response(
            b"<html><body>"
            b'<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
            b'<a href="targum_onkelos_jonathan.html">'
            b"Targums Onkelos and Jonathan to the Prophets"
            b"</a>"
            b"</body></html>"
        )
    )

    assert [(item.category_id, item.label) for item in page.categories] == [
        ("3", "Biblical Aramaic"),
        ("51", "Targums Onkelos and Jonathan to the Prophets"),
    ]


def test_dedicated_onkelos_jonathan_route_preserves_changed_nonempty_label() -> None:
    page = parse_text_catalogue_page(
        _response(
            b"<html><body>"
            b'<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
            b'<a href="targum_onkelos_jonathan.html">Onkelos and Jonathan Targums</a>'
            b"</body></html>"
        )
    )

    assert [(item.category_id, item.label) for item in page.categories] == [
        ("3", "Biblical Aramaic"),
        ("51", "Onkelos and Jonathan Targums"),
    ]


def test_changed_onkelos_jonathan_root_route_fails_closed() -> None:
    response = _response(
        b"<html><body>"
        b'<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
        b'<a href="changed_targum_route.html">'
        b"Targums Onkelos and Jonathan to the Prophets"
        b"</a>"
        b"</body></html>"
    )

    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)


def test_dedicated_collection_keeps_subdivided_and_direct_children_distinct() -> None:
    page = parse_text_catalogue_page(
        _response(
            b"<html><body>"
            b'<a href="showsubtexts.php?cset=H&amp;subtext=51001">51001 TgO Gn</a>'
            b'<a href="get_a_chapter.php?cset=H&amp;file=51400">'
            b"51400 MegTan (Megillat Taanit)"
            b"</a>"
            b"</body></html>",
            "https://cal.huc.edu/targum_onkelos_jonathan.html",
        )
    )

    assert [(item.category_id, item.label) for item in page.categories] == [
        ("51001", "51001 TgO Gn")
    ]
    assert [(item.file_id, item.subtext_id, item.label) for item in page.texts] == [
        ("51400", None, "51400 MegTan (Megillat Taanit)")
    ]


class RecordingTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return _response(
            b'<html><body><a href="get_a_chapter.php?file=51400">MegTan</a></body></html>',
            "https://cal.huc.edu/targum_onkelos_jonathan.html",
        )


@pytest.mark.anyio
async def test_category_51_dispatches_to_dedicated_collection_once() -> None:
    transport = RecordingTransport()
    service = TextService(CalHttpClient(transport=transport))

    result = await service.catalogue(category_id="51")

    assert transport.requests == [CalRequest(method="GET", path="targum_onkelos_jonathan.html")]
    assert result.provenance.category_id == "51"


@pytest.mark.anyio
async def test_ordinary_category_dispatch_remains_unchanged() -> None:
    transport = RecordingTransport()
    service = TextService(CalHttpClient(transport=transport))

    await service.catalogue(category_id="3")

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="showsubtexts.php",
            params=(("subtext", "3"),),
        )
    ]
