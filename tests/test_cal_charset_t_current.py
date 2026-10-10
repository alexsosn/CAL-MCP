"""Issue #254: CAL's current ``cset=T`` (Unicode transliteration) selector.

See R-073.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import (
    ConcordanceParseError,
    ConcordanceService,
    parse_kwic_full_context_page,
)
from cal_mcp.errors import CalInputError
from cal_mcp.texts import TextParseError, parse_text_search_page

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
KWIC_DIALECT = FIXTURES / "kwic_dialect_mlk_1_charset_t_current.html"
FULL_CONTEXT = FIXTURES / "kwic_full_context_fakh_11200_2_charset_t_current.html"
TEXT_SEARCH = FIXTURES / "text_search_palmyr_charset_t_current.html"
RETRIEVED_AT = datetime(2026, 10, 10, tzinfo=UTC)
FULL_CONTEXT_URL = (
    "https://cal.huc.edu/get_a_kwicchapter.php?file=11200&sub=2&cset=T&target=11200206"
)


def _response(url: str, body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


class _Transport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_old_aramaic_dialect_kwic_preserves_charset_t_hits() -> None:
    transport = _Transport(
        _response(
            "https://cal.huc.edu/show1dialectKWIC.php?lemma=mlk&pos=N&texts=1",
            KWIC_DIALECT.read_bytes(),
        )
    )
    client = CalHttpClient(transport=transport)
    try:
        result = await ConcordanceService(client).kwic_dialect("mlk N", "1")
    finally:
        await client.aclose()

    assert result.total == 3
    assert [
        (hit.file_id, hit.subtext_id, hit.target_coordinate, hit.charset) for hit in result.hits
    ] == [
        ("11200", "2", "11200206", "T"),
        ("11200", "2", "11200207", "T"),
        ("11200", "2", "11200213", "T"),
    ]
    assert result.hits[0].full_context_url == (
        "https://cal.huc.edu/get_a_kwicchapter.php?file=11200&sub=2&cset=T&target=11200206"
    )


@pytest.mark.anyio
async def test_unknown_kwic_charset_letter_still_fails_closed() -> None:
    body = KWIC_DIALECT.read_bytes().replace(b"cset=T&target=11200207", b"cset=Q&target=11200207")
    transport = _Transport(
        _response("https://cal.huc.edu/show1dialectKWIC.php?lemma=mlk&pos=N&texts=1", body)
    )
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(ConcordanceParseError, match="unknown charset"):
            await ConcordanceService(client).kwic_dialect("mlk N", "1")
    finally:
        await client.aclose()


def test_charset_t_full_context_page_parses_transliterated_rows() -> None:
    page = parse_kwic_full_context_page(
        _response(FULL_CONTEXT_URL, FULL_CONTEXT.read_bytes()),
        requested_file_id="11200",
        requested_subtext_id="2",
        requested_target_coordinate="11200206",
        requested_charset="T",
    )

    assert page.status.value == "found"
    assert [line.coordinate for line in page.lines] == ["11200205", "11200206", "11200207"]
    assert [token.text for token in page.lines[1].tokens][:5] == [
        "skn",
        "mrʾ",
        "rb",
        "mrʾ",
        "hdysʿy",
    ]


@pytest.mark.anyio
async def test_full_context_service_accepts_returned_charset_t() -> None:
    transport = _Transport(_response(FULL_CONTEXT_URL, FULL_CONTEXT.read_bytes()))
    client = CalHttpClient(transport=transport)
    try:
        result = await ConcordanceService(client).kwic_full_context(
            "11200", "11200206", "T", subtext_id="2"
        )
    finally:
        await client.aclose()

    assert result.charset == "T"
    assert dict(transport.requests[0].params)["cset"] == "T"


@pytest.mark.anyio
async def test_full_context_service_still_rejects_other_charsets_before_transport() -> None:
    transport = _Transport(_response(FULL_CONTEXT_URL, FULL_CONTEXT.read_bytes()))
    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(CalInputError, match="H, R, S, T, U"):
            await ConcordanceService(client).kwic_full_context("11200", "11200206", "Q")
    finally:
        await client.aclose()
    assert transport.requests == []


def test_palmyrene_text_search_keeps_charset_t_catalogue_nodes() -> None:
    page = parse_text_search_page(
        _response("https://cal.huc.edu/newsearchtxts.php", TEXT_SEARCH.read_bytes())
    )

    assert [
        (match.file_id, match.category_id, match.label, match.follow_up_tool)
        for match in page.matches
    ] == [
        (None, "2035043", "ImaOss", "cal_text_catalogue"),
        (None, "41201", "Palm 1-742", "cal_text_catalogue"),
        (None, "41201001", "C3901 (PAT 0246)", "cal_text_catalogue"),
        (None, "41202", "Palm 743-1148", "cal_text_catalogue"),
    ]


def test_text_search_unknown_cset_letter_still_fails_closed() -> None:
    body = TEXT_SEARCH.read_bytes().replace(b"subtext=41202&cset=T", b"subtext=41202&cset=Q")

    with pytest.raises(TextParseError, match="invalid cset"):
        parse_text_search_page(_response("https://cal.huc.edu/newsearchtxts.php", body))
