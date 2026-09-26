"""Issue #170: CPA subtext IDs are digits plus an optional lowercase suffix."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceService,
    KwicScopeKind,
    parse_kwic_result,
)
from cal_mcp.identifiers import is_cal_subtext_id
from cal_mcp.lexicon import _Line, _Link
from cal_mcp.texts import TextParseError, TextService, _page_navigation, parse_text_catalogue_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 26, tzinfo=UTC)
CATALOGUE = FIXTURES / "cpa_catalogue_alphanumeric_current.html"
PAGE = FIXTURES / "cpa_text_page_alphanumeric_structural.html"
KWIC = FIXTURES / "kwic_dialect_nqh_n_forms_current.html"
FULL_CONTEXT_NOT_FOUND = FIXTURES / "kwic_full_context_not_found.html"


def _response(body: bytes, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


class CpaTextTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        query = urlencode(request.params)
        url = f"https://cal.huc.edu/{request.path}?{query}"
        if request.path == "showsubtexts.php":
            return _response(CATALOGUE.read_bytes(), url)
        if request.path == "get_a_chapter.php":
            return _response(PAGE.read_bytes(), url)
        if request.path == "get_file_info.php":
            return _response(
                b"<html><body><h1>Text Information</h1><p>fixture metadata</p></body></html>",
                url,
            )
        raise AssertionError(f"unexpected request: {request!r}")


@pytest.mark.anyio
async def test_cpa_catalogue_preserves_alphanumeric_subtext_id() -> None:
    transport = CpaTextTransport()
    service = TextService(CalHttpClient(transport=transport))

    result = await service.catalogue(category_id="55")

    assert [(text.file_id, text.subtext_id, text.label) for text in result.texts] == [
        ("55000", "01001a", "Gen 19 Damascus frag V")
    ]
    assert len(transport.requests) == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("001", True),
        ("01001a", True),
        ("9z", True),
        ("a01001", False),
        ("01001ab", False),
        ("01001A", False),
        ("01-001a", False),
        (" 01001a", False),
        ("", False),
        (None, False),
    ],
)
def test_shared_subtext_id_grammar_is_narrow(value: object, expected: bool) -> None:
    assert is_cal_subtext_id(value) is expected


@pytest.mark.parametrize(
    "mutated_href",
    [
        "/get_a_chapter.php?file=55000&sub=01001a&cset=R",
        "/get_a_chapter.php?file=55000&sub=01001a",
        "/get_a_chapter.php?file=55000&sub=01001a&cset=C&extra=1",
    ],
)
def test_cpa_catalogue_suffix_requires_exact_current_cset_route(mutated_href: str) -> None:
    body = CATALOGUE.read_text(encoding="utf-8")
    original = "/get_a_chapter.php?file=55000&sub=01001a&cset=C"
    assert original in body
    response = _response(
        body.replace(original, mutated_href, 1).encode(),
        "https://cal.huc.edu/showsubtexts.php?subtext=55",
    )
    with pytest.raises(TextParseError):
        parse_text_catalogue_page(response)


@pytest.mark.parametrize("cset", ["R", "", "CC"])
def test_cpa_navigation_requires_current_cset(cset: str) -> None:
    suffix = f"&cset={cset}" if cset else ""
    line = _Line(
        text="NEXT PAGE",
        links=(
            _Link(
                href=f"/get_a_chapter.php?file=55000&sub=01001a&page=1{suffix}",
                text="NEXT PAGE",
            ),
        ),
        list_depth=0,
    )
    with pytest.raises(TextParseError, match="cset=C"):
        _page_navigation(
            [line],
            requested_file_id="55000",
            requested_subtext_id="01001a",
        )


def test_cpa_navigation_accepts_current_cset() -> None:
    line = _Line(
        text="NEXT PAGE",
        links=(
            _Link(
                href="/get_a_chapter.php?file=55000&sub=01001a&page=1&cset=C",
                text="NEXT PAGE",
            ),
        ),
        list_depth=0,
    )
    assert _page_navigation(
        [line],
        requested_file_id="55000",
        requested_subtext_id="01001a",
    ) == (None, 2)


@pytest.mark.anyio
async def test_cpa_page_accepts_suffix_and_uses_current_cset() -> None:
    transport = CpaTextTransport()
    service = TextService(CalHttpClient(transport=transport))

    result = await service.page("55000", subtext_id="01001a")

    assert len(transport.requests) == 1
    [request] = transport.requests
    assert request.path == "get_a_chapter.php"
    assert dict(request.params) == {
        "file": "55000",
        "sub": "01001a",
        "cset": "C",
        "page": "0",
    }
    assert result.page is not None
    assert result.page.text.file_id == "55000"
    assert result.page.text.subtext_id == "01001a"
    assert result.page.lines[0].text == "fixture-token"


@pytest.mark.anyio
async def test_cpa_information_composes_alphanumeric_subtext_id() -> None:
    transport = CpaTextTransport()
    service = TextService(CalHttpClient(transport=transport))

    result = await service.information("55000", subtext_id="01001a")

    assert len(transport.requests) == 1
    [request] = transport.requests
    assert request.path == "get_file_info.php"
    assert request.params == (("coord", "5500001001a"),)
    assert result.file_id == "55000"
    assert result.subtext_id == "01001a"


@pytest.mark.anyio
@pytest.mark.parametrize("bad", ["a01001", "01001ab", "01001A", "01-001a", " 01001a", ""])
async def test_text_services_still_reject_non_subtext_shapes(bad: str) -> None:
    for operation in ("page", "information"):
        transport = CpaTextTransport()
        service = TextService(CalHttpClient(transport=transport))
        with pytest.raises(ValueError):
            if operation == "page":
                await service.page("55000", subtext_id=bad)
            else:
                await service.information("55000", subtext_id=bad)
        assert transport.requests == []


class FullContextTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        query = urlencode(request.params)
        return _response(
            FULL_CONTEXT_NOT_FOUND.read_bytes(),
            f"https://cal.huc.edu/{request.path}?{query}",
        )


@pytest.mark.anyio
async def test_kwic_full_context_accepts_alphanumeric_subtext_id() -> None:
    transport = FullContextTransport()
    service = ConcordanceService(CalHttpClient(transport=transport))

    result = await service.kwic_full_context(
        "13250",
        "999999999999",
        "R",
        subtext_id="01001a",
    )

    assert result.status.value == "not_found"
    assert result.subtext_id == "01001a"
    assert len(transport.requests) == 1
    [request] = transport.requests
    assert dict(request.params) == {
        "file": "13250",
        "sub": "01001a",
        "cset": "R",
        "target": "999999999999",
    }


@pytest.mark.anyio
@pytest.mark.parametrize("bad", ["a01001", "01001ab", "01001A", "01-001a"])
async def test_kwic_full_context_rejects_non_subtext_shapes_before_transport(bad: str) -> None:
    transport = FullContextTransport()
    service = ConcordanceService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await service.kwic_full_context(
            "13250",
            "999999999999",
            "R",
            subtext_id=bad,
        )

    assert transport.requests == []


def _kwic_with_subtext(subtext_id: str) -> object:
    body = KWIC.read_text(encoding="utf-8")
    assert "sub=53" in body
    body = body.replace("sub=53", f"sub={subtext_id}")
    return parse_kwic_result(
        _response(
            body.encode(),
            "https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts=6",
        ),
        lemma_key="n)qh N",
        scope_kind=KwicScopeKind.DIALECT,
        scope_ids=("6",),
    )


def test_returned_kwic_hit_preserves_alphanumeric_subtext_id() -> None:
    page = _kwic_with_subtext("01001a")
    assert page.hits[0].subtext_id == "01001a"


def test_returned_kwic_hit_rejects_broader_alphanumeric_shape() -> None:
    with pytest.raises(ConcordanceParseError):
        _kwic_with_subtext("01001ab")
