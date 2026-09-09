from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextParseError, TextService, parse_text_catalogue_page

_RETRIEVED_AT = datetime(2026, 9, 10, tzinfo=UTC)
_ROOT_URL = "https://cal.huc.edu/newtextmenu.html"
_EXPECTED_SELECTORS = (
    "ot-peshitta",
    "old-syriac-gospels",
    "nt-peshitta",
    "apocryphal-pseudepigraphal",
    "commentaries",
    "metrical-homilies-hymns",
    "dispute-poems",
    "religion",
    "archival",
    "canonical",
    "documents",
    "syro-roman-law-book",
    "canon-law",
    "magic",
    "science-philosophy",
    "history",
    "novels-histories",
    "martyrologies",
    "various",
    "inscriptions",
)


def _response(body: str, url: str = _ROOT_URL) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=_RETRIEVED_AT,
    )


def _specialized(page: object) -> tuple[object, ...]:
    value = getattr(page, "specialized_collections", None)
    assert isinstance(value, tuple), "catalogue page must expose specialized_collections"
    return value


def _selector_helper() -> Callable[[], tuple[str, ...]]:
    module = importlib.import_module("cal_mcp.syriac")
    helper = getattr(module, "syriac_text_category_slugs", None)
    assert callable(helper), "syriac_text_category_slugs must expose the service selector config"
    return cast(Callable[[], tuple[str, ...]], helper)


def test_root_catalogue_preserves_syriac_as_operation_aware_specialized_collection() -> None:
    page = parse_text_catalogue_page(
        _response(
            "<html><body>"
            '<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
            '<a href="targum_onkelos_jonathan.html">'
            "Targums Onkelos and Jonathan to the Prophets"
            "</a>"
            '<a href="AvailSyr.html">Syriac</a>'
            '<a href="show_Mandaic.php?R1=74">Mandaic</a>'
            "</body></html>"
        )
    )

    assert [(item.category_id, item.label) for item in page.categories] == [
        ("3", "Biblical Aramaic"),
        ("51", "Targums Onkelos and Jonathan to the Prophets"),
        ("74", "Mandaic"),
    ]
    specialized = _specialized(page)
    assert len(specialized) == 1
    item = specialized[0]
    assert getattr(item, "collection_key", None) == "syriac"
    assert getattr(item, "label", None) == "Syriac"
    assert getattr(item, "follow_up_tool", None) == "cal_syriac_texts"
    assert getattr(item, "selector_name", None) == "category"
    assert getattr(item, "supported_selectors", None) == _EXPECTED_SELECTORS


def test_syriac_selector_metadata_comes_from_the_service_configuration() -> None:
    assert _selector_helper()() == _EXPECTED_SELECTORS
    assert len(set(_EXPECTED_SELECTORS)) == len(_EXPECTED_SELECTORS)
    assert all(not selector.isdecimal() for selector in _EXPECTED_SELECTORS)


def test_exact_syriac_root_route_preserves_changed_nonempty_label() -> None:
    page = parse_text_catalogue_page(
        _response('<a href="AvailSyr.html">Syriac texts by classification</a>')
    )

    specialized = _specialized(page)
    assert len(specialized) == 1
    assert getattr(specialized[0], "label", None) == "Syriac texts by classification"


@pytest.mark.parametrize(
    "href",
    [
        "changed-syriac.html",
        "legacy/AvailSyr.html",
        "AvailSyr.html?category=all",
        "AvailSyr.html#texts",
        "https://example.org/AvailSyr.html",
    ],
)
def test_syriac_labelled_changed_root_route_fails_closed(href: str) -> None:
    response = _response(
        "<html><body>"
        '<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
        f'<a href="{href}">Syriac</a>'
        "</body></html>"
    )

    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)


def test_exact_syriac_route_with_empty_label_fails_closed() -> None:
    response = _response(
        "<html><body>"
        '<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
        '<p>specialized collection <a href="AvailSyr.html"></a></p>'
        "</body></html>"
    )

    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)


def test_duplicate_syriac_specialized_collection_fails_closed() -> None:
    response = _response(
        "<html><body>"
        '<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
        '<a href="AvailSyr.html">Syriac</a>'
        '<a href="/AvailSyr.html">Syriac classification</a>'
        "</body></html>"
    )

    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)


def test_non_root_catalogue_does_not_apply_syriac_root_drift_rules() -> None:
    page = parse_text_catalogue_page(
        _response(
            '<a href="get_a_chapter.php?file=10001">Syriac</a>',
            "https://cal.huc.edu/showsubtexts.php?subtext=3",
        )
    )

    assert [(item.file_id, item.label) for item in page.texts] == [("10001", "Syriac")]
    assert _specialized(page) == ()


def test_non_root_exact_availsyr_link_is_not_specialized_metadata() -> None:
    page = parse_text_catalogue_page(
        _response(
            "<html><body>"
            '<a href="get_a_chapter.php?file=10001">One text</a>'
            '<a href="AvailSyr.html">Syriac</a>'
            "</body></html>",
            "https://cal.huc.edu/showsubtexts.php?subtext=3",
        )
    )

    assert [(item.file_id, item.label) for item in page.texts] == [("10001", "One text")]
    assert _specialized(page) == ()


def test_foreign_root_path_does_not_enable_syriac_specialized_metadata() -> None:
    page = parse_text_catalogue_page(
        _response(
            "<html><body>"
            '<a href="get_a_chapter.php?file=10001">One text</a>'
            '<a href="AvailSyr.html">Syriac</a>'
            "</body></html>",
            "https://example.org/newtextmenu.html",
        )
    )

    assert [(item.file_id, item.label) for item in page.texts] == [("10001", "One text")]
    assert _specialized(page) == ()


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_root_service_discovers_syriac_without_prefetching_availsyr() -> None:
    transport = RecordingTransport(
        _response(
            "<html><body>"
            '<a href="showsubtexts.php?subtext=3">Biblical Aramaic</a>'
            '<a href="AvailSyr.html">Syriac</a>'
            "</body></html>"
        )
    )
    service = TextService(CalHttpClient(transport=transport))

    result = await service.catalogue()

    assert transport.requests == [CalRequest(method="GET", path="newtextmenu.html")]
    specialized = _specialized(result)
    assert len(specialized) == 1
    payload = result.to_dict()
    assert isinstance(payload.get("specialized_collections"), list)
    assert payload["specialized_collections"] == [
        {
            "collection_key": "syriac",
            "label": "Syriac",
            "follow_up_tool": "cal_syriac_texts",
            "selector_name": "category",
            "supported_selectors": list(_EXPECTED_SELECTORS),
        }
    ]
    assert result.provenance.source_url == _ROOT_URL


@pytest.mark.anyio
async def test_non_root_catalogue_serializes_an_empty_specialized_collection_list() -> None:
    transport = RecordingTransport(
        _response(
            '<a href="get_a_chapter.php?file=10001">One text</a>',
            "https://cal.huc.edu/showsubtexts.php?subtext=3",
        )
    )
    service = TextService(CalHttpClient(transport=transport))

    result = await service.catalogue(category_id="3")

    assert transport.requests == [
        CalRequest(method="GET", path="showsubtexts.php", params=(("subtext", "3"),))
    ]
    assert _specialized(result) == ()
    assert result.to_dict().get("specialized_collections") == []
