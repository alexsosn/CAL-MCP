from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.search import (
    EnglishSearchService,
    SearchParseError,
    parse_citation_search_page,
    parse_gloss_search_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 4, 21, 0, tzinfo=UTC)


def _response(name: str, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def test_gloss_search_parser_preserves_ordered_cal_lemma_refs() -> None:
    page = parse_gloss_search_page(
        _response("search_gloss_camel.html", "https://cal.huc.edu/newsearchmngs.php")
    )

    assert [item.lemma_key for item in page.matches] == ["bwkty N", "gml N", "ynqh N"]
    assert page.matches[0].headwords == ("[bwkty]",)
    assert page.matches[0].part_of_speech == "n.m."
    assert page.matches[0].gloss == "bactrian camel"
    assert page.matches[1].headwords == ("gml", "gmlˀ")
    assert page.matches[1].gloss == "camel; beam"


def test_gloss_search_parser_preserves_explicit_empty_result() -> None:
    page = parse_gloss_search_page(
        _response("search_gloss_empty.html", "https://cal.huc.edu/newsearchmngs.php")
    )

    assert page.matches == ()


def test_citation_search_parser_preserves_lemma_context_and_unicode_citation() -> None:
    page = parse_citation_search_page(
        _response("search_citations_camel.html", "https://cal.huc.edu/searchcits.php")
    )

    assert len(page.hits) == 3
    first = page.hits[0]
    assert first.lemma.lemma_key == ")w c"
    assert first.lemma.headwords == ("ˀw",)
    assert first.lexical_context.startswith("or : with comparative adjs.")
    assert first.reference == "OS MkSin10:25"
    assert first.source_text.startswith("ܦܫܝܩ ܗܘ")
    assert first.translation == "for it is easier for a camel to enter into the needle’s hole"

    second = page.hits[1]
    third = page.hits[2]
    assert second.lemma.lemma_key == "gml N"
    assert third.lemma.lemma_key == "gml N"
    assert second.reference == "AradOstr.24.1"
    assert second.source_text == "גמל 1 חמר 2"
    assert third.reference == "TAD D.22.1:2"


def test_citation_search_parser_preserves_explicit_empty_result() -> None:
    page = parse_citation_search_page(
        _response("search_citations_empty.html", "https://cal.huc.edu/searchcits.php")
    )

    assert page.hits == ()


def test_citation_search_parser_fails_on_unrecognized_nonempty_shape() -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/searchcits.php",
        body=b"<html><body><div>camel; beam</div><div>citation-like text</div></body></html>",
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )

    with pytest.raises(SearchParseError):
        parse_citation_search_page(response)


class FixtureSearchTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.path == "newsearchmngs.php":
            return _response("search_gloss_camel.html", "https://cal.huc.edu/newsearchmngs.php")
        if request.path == "searchcits.php":
            return _response("search_citations_camel.html", "https://cal.huc.edu/searchcits.php")
        raise AssertionError(f"unexpected CAL path: {request.path}")


@pytest.mark.anyio
async def test_gloss_search_uses_current_post_contract_and_preserves_provenance() -> None:
    transport = FixtureSearchTransport()
    service = EnglishSearchService(CalHttpClient(transport=transport))

    result = await service.search_gloss(" camel# ", all_glosses=True)

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.method == "POST"
    assert request.path == "newsearchmngs.php"
    assert request.params == ()
    assert request.data == (("English", "camel#"), ("secondary", "true"))
    assert [item.lemma_key for item in result.matches] == ["bwkty N", "gml N", "ynqh N"]
    assert result.all_glosses is True
    assert result.provenance.source == "CAL"
    assert result.provenance.source_url == "https://cal.huc.edu/newsearchmngs.php"
    assert result.provenance.retrieved_at == RETRIEVED_AT
    assert result.provenance.original_query == " camel# "
    assert result.provenance.submitted_query == "camel#"
    assert result.provenance.search_kind == "gloss"


@pytest.mark.anyio
async def test_primary_gloss_search_sends_empty_secondary_radio_value() -> None:
    transport = FixtureSearchTransport()
    service = EnglishSearchService(CalHttpClient(transport=transport))

    await service.search_gloss("camel")

    assert transport.requests[0].data == (("English", "camel"), ("secondary", ""))


@pytest.mark.anyio
async def test_citation_search_uses_current_post_contract_once() -> None:
    transport = FixtureSearchTransport()
    service = EnglishSearchService(CalHttpClient(transport=transport))

    result = await service.search_citations(" camel ")

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.method == "POST"
    assert request.path == "searchcits.php"
    assert request.params == ()
    assert request.data == (("English", "camel"),)
    assert len(result.hits) == 3
    assert result.provenance.original_query == " camel "
    assert result.provenance.submitted_query == "camel"
    assert result.provenance.search_kind == "citation_text"


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["", "   ", "one two three four"])
async def test_invalid_citation_search_is_rejected_before_transport(query: str) -> None:
    transport = FixtureSearchTransport()
    service = EnglishSearchService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await service.search_citations(query)

    assert transport.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["", "  ", "ab", "ab#"])
async def test_invalid_gloss_search_is_rejected_before_transport(query: str) -> None:
    transport = FixtureSearchTransport()
    service = EnglishSearchService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await service.search_gloss(query)

    assert transport.requests == []
