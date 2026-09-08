from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import (
    TextCatalogueResult,
    TextParseError,
    TextProvenance,
    TextService,
    parse_text_catalogue_page,
)

_RETRIEVED_AT = datetime(2026, 9, 8, tzinfo=UTC)


def _response(body: bytes, url: str = "https://cal.huc.edu/newtextmenu.html") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def test_root_catalogue_preserves_current_specialized_collection_routes() -> None:
    page = parse_text_catalogue_page(
        _response(
            b"<html><body>"
            b'<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
            b'<a href="get_a_chapter.php?cset=H&amp;file=13250">Tel Dan Stele</a>'
            b'<a href="targum_onkelos_jonathan.html">Targums Onkelos and Jonathan</a>'
            b'<a href="AvailSyr.html">Syriac</a>'
            b'<a href="show_Mandaic.php?R1=74">Mandaic</a>'
            b"</body></html>"
        )
    )

    assert [(item.category_id, item.label) for item in page.categories] == [
        ("3", "Biblical Aramaic")
    ]
    assert [(item.file_id, item.label) for item in page.texts] == [
        ("13250", "Tel Dan Stele")
    ]
    assert [
        (item.collection_id, item.label, item.follow_up_tool, item.category_id)
        for item in page.collections
    ] == [
        (
            "targum-onkelos-jonathan",
            "Targums Onkelos and Jonathan",
            "cal_text_catalogue",
            "51",
        ),
        ("syriac", "Syriac", "cal_syriac_texts", None),
        ("mandaic", "Mandaic", "cal_text_catalogue", "74"),
    ]


def test_known_mandaic_collection_link_with_wrong_selector_is_parser_drift() -> None:
    response = _response(
        b"<html><body>"
        b'<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
        b'<a href="show_Mandaic.php?R1=75">Mandaic</a>'
        b"</body></html>"
    )

    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)


class RecordingCatalogueTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return _response(
            b'<html><body><a href="get_a_chapter.php?file=13250">text</a></body></html>',
            "https://cal.huc.edu/fixture",
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("category_id", "expected_request"),
    [
        (
            "51",
            CalRequest(method="GET", path="targum_onkelos_jonathan.html"),
        ),
        (
            "74",
            CalRequest(
                method="GET",
                path="show_Mandaic.php",
                params=(("R1", "74"),),
            ),
        ),
        (
            "3",
            CalRequest(
                method="GET",
                path="showsubtexts.php",
                params=(("subtext", "3"),),
            ),
        ),
    ],
)
async def test_catalogue_dispatches_current_route_family(
    category_id: str,
    expected_request: CalRequest,
) -> None:
    transport = RecordingCatalogueTransport()
    service = TextService(CalHttpClient(transport=transport))

    await service.catalogue(category_id=category_id)

    assert transport.requests == [expected_request]


def test_text_catalogue_serialization_exposes_collections_key() -> None:
    result = TextCatalogueResult(
        categories=(),
        texts=(),
        provenance=TextProvenance(
            source="CAL",
            source_url="https://cal.huc.edu/newtextmenu.html",
            retrieved_at=_RETRIEVED_AT,
            operation="catalogue",
        ),
    )

    assert result.to_dict()["collections"] == []
