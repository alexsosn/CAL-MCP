from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.syriac import SyriacParseError, SyriacService, parse_syriac_text_category_page
from cal_mcp.texts import TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 9, tzinfo=UTC)


def _fixture_response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _inline_response(body: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


@pytest.mark.parametrize(
    ("category", "fixture", "url", "expected"),
    [
        (
            "ot-peshitta",
            "syriac_category_ot_peshitta_current.html",
            "https://cal.huc.edu/ot_peshitta.html",
            [("62001", "P Gn"), ("62002", "P Ex")],
        ),
        (
            "nt-peshitta",
            "syriac_category_nt_peshitta_current.html",
            "https://cal.huc.edu/nt_peshitta.html",
            [("62040", "P Mt"), ("62041", "P Mk")],
        ),
    ],
)
def test_current_peshitta_book_links_are_catalogue_navigation(
    category: str,
    fixture: str,
    url: str,
    expected: list[tuple[str, str]],
) -> None:
    page = parse_syriac_text_category_page(
        _fixture_response(fixture, url),
        category=category,
    )

    assert [(item.upstream_id, item.label) for item in page.items] == expected
    assert [item.navigation_kind.value for item in page.items] == ["catalogue"] * len(expected)
    assert all("subtext=" in item.navigation_url for item in page.items)
    assert all("cset=Syriac" in item.navigation_url for item in page.items)


@pytest.mark.parametrize(
    "href",
    [
        "/showsubtexts.php?keyword=62001&subtext=62001",
        "/showsubtexts.php?subtext=62001&subtext=62002",
        "/showsubtexts.php?keyword=62001&keyword=62002",
        "/showsubtexts.php?subtext=",
        "/showsubtexts.php?subtext=not-a-decimal",
        "/showsubtexts.php?cset=Syriac",
    ],
)
def test_syriac_showsubtexts_requires_one_unambiguous_semantic_selector(href: str) -> None:
    body = (
        "<h1>OT Peshiṭta</h1><ul><li>"
        f'<a href="{href}">62001</a> P Gn '
        '<a href="/get_file_info.php?coord=62001">ⓘ</a>'
        "</li></ul>"
    )
    with pytest.raises(SyriacParseError):
        parse_syriac_text_category_page(
            _inline_response(body, "https://cal.huc.edu/ot_peshitta.html"),
            category="ot-peshitta",
        )


class CurrentPeshittaTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.path == "ot_peshitta.html":
            return _fixture_response(
                "syriac_category_ot_peshitta_current.html",
                "https://cal.huc.edu/ot_peshitta.html",
            )
        raise AssertionError(f"unexpected request: {request!r}")


@pytest.mark.anyio
async def test_syriac_peshitta_category_remains_one_request_and_does_not_prefetch_chapters() -> None:
    transport = CurrentPeshittaTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await SyriacService(client).texts("ot-peshitta")
    finally:
        await client.aclose()

    assert [(item.upstream_id, item.navigation_kind.value) for item in result.items] == [
        ("62001", "catalogue"),
        ("62002", "catalogue"),
    ]
    assert transport.requests == [CalRequest(method="GET", path="ot_peshitta.html")]


class PeshittaCatalogueTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return _fixture_response(
            "text_catalogue_peshitta_genesis.html",
            "https://cal.huc.edu/showsubtexts.php?subtext=62001",
        )


@pytest.mark.anyio
async def test_catalogue_navigation_has_existing_one_request_mcp_native_followup() -> None:
    transport = PeshittaCatalogueTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TextService(client).catalogue(category_id="62001")
    finally:
        await client.aclose()

    assert transport.requests == [
        CalRequest(
            method="GET",
            path="showsubtexts.php",
            params=(("subtext", "62001"),),
        )
    ]
    assert result.categories == ()
    assert [(item.file_id, item.subtext_id, item.label) for item in result.texts] == [
        ("62001", "01", "chapter 1"),
        ("62001", "02", "chapter 2"),
    ]
    assert result.provenance.category_id == "62001"
