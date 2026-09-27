from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.token_analysis import (
    TokenAnalysisParseError,
    TokenAnalysisService,
    TokenAnalysisStatus,
    parse_token_analysis_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 27, tzinfo=UTC)
PESHITTA_SIMPLE = FIXTURES / "token_analysis_linkless_peshitta_simple_current.html"
PESHITTA_MULTI = FIXTURES / "token_analysis_linkless_peshitta_multi_current.html"
CPA_SIMPLE = FIXTURES / "token_analysis_linkless_cpa_simple_current.html"
NO_DATA = FIXTURES / "token_analysis_not_found.html"
LINKED = FIXTURES / "token_analysis_syriac_redirect_current.html"


def _response(body: str, *, url: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


@pytest.mark.parametrize(
    ("fixture", "url", "expected"),
    [
        (
            PESHITTA_SIMPLE,
            "https://cal.huc.edu/getlex.php?coord=620570101&word=0",
            ("pwlws PN Personal name",),
        ),
        (
            PESHITTA_MULTI,
            "https://cal.huc.edu/getlex.php?coord=620570101&word=2",
            ("d_ p = d_ p --> dy p", "y$w( PN Personal name"),
        ),
        (
            CPA_SIMPLE,
            "https://cal.huc.edu/getlex.php?coord=5500001001a019001&word=0",
            ("lwT PN Personal name",),
        ),
    ],
)
def test_linkless_current_summary_is_preserved_without_invented_candidate(
    fixture: Path,
    url: str,
    expected: tuple[str, ...],
) -> None:
    page = parse_token_analysis_page(_response(fixture.read_text(encoding="utf-8"), url=url))

    assert page.candidates == ()
    assert page.unlinked_summaries == expected


def test_explicit_no_data_keeps_both_result_collections_empty() -> None:
    page = parse_token_analysis_page(
        _response(
            NO_DATA.read_text(encoding="utf-8"),
            url="https://cal.huc.edu/getlex.php?coord=9999999999999&word=0",
        )
    )

    assert page.candidates == ()
    assert page.unlinked_summaries == ()


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_service_reports_found_and_serializes_unlinked_summaries() -> None:
    response = _response(
        PESHITTA_MULTI.read_text(encoding="utf-8"),
        url="https://cal.huc.edu/getlex.php?coord=620570101&word=2",
    )
    transport = RecordingTransport(response)

    result = await TokenAnalysisService(CalHttpClient(transport=transport)).analyze(
        "620570101",
        2,
    )

    assert result.status is TokenAnalysisStatus.FOUND
    assert result.candidates == ()
    assert result.unlinked_summaries == (
        "d_ p = d_ p --> dy p",
        "y$w( PN Personal name",
    )
    structured = result.to_dict()
    assert structured["candidates"] == []
    assert structured["unlinked_summaries"] == [
        "d_ p = d_ p --> dy p",
        "y$w( PN Personal name",
    ]
    assert len(transport.requests) == 1


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><h2>Click on a headword to see a complete lexicon entry</h2>"
        '<br><a href="/unexpected.php">opaque</a><br>'
        '<a href="/newtextmenu.html">Return to the Text Browser</a></body></html>',
        "<html><body><h2>Click on a headword to see a complete lexicon entry</h2>"
        "<br>opaque summary<br><table><tr><td>unexpected table text</td></tr></table>"
        '<a href="/newtextmenu.html">Return to the Text Browser</a></body></html>',
        "<html><body><h2>Click on a headword to see a complete lexicon entry</h2>"
        "<br>opaque summary<br>"
        '<a class="lexlink" href="oneentry.php?lemma=x+N&cits=all">x n. gloss</a>'
        '<a href="/newtextmenu.html">Return to the Text Browser</a></body></html>',
    ],
)
def test_linkless_shape_with_links_or_table_fails_closed(body: str) -> None:
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(
            _response(
                body,
                url="https://cal.huc.edu/getlex.php?coord=620570101&word=0",
            )
        )


def test_marker_only_stays_parser_drift() -> None:
    body = (
        "<html><body><h2>Click on a headword to see a complete lexicon entry</h2>"
        '<br><a href="/newtextmenu.html">Return to the Text Browser</a></body></html>'
    )
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(
            _response(
                body,
                url="https://cal.huc.edu/getlex.php?coord=620570101&word=0",
            )
        )


def test_linked_current_shape_keeps_empty_unlinked_summary_collection() -> None:
    page = parse_token_analysis_page(
        _response(
            LINKED.read_text(encoding="utf-8"),
            url="https://cal.huc.edu/getlex.php?coord=620570101&word=1",
        )
    )

    assert len(page.candidates) == 1
    assert page.unlinked_summaries == ()


def test_no_lemma_state_mixed_with_unlinked_summary_fails_closed() -> None:
    body = (
        "<html><body>"
        "<div>Click on a headword to see a complete lexicon entry</div>"
        '<div>| W.D. "unrecognizable query or no such lemma found"</div>'
        "<div>opaque extra summary</div>"
        '<div><a href="/newtextmenu.html">Return to the Text Browser</a></div>'
        "</body></html>"
    )
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(
            _response(
                body,
                url="https://cal.huc.edu/getlex.php?coord=1325007&word=1",
            )
        )


def test_no_data_state_mixed_with_unrelated_text_fails_closed() -> None:
    body = (
        "<html><body>"
        "<div>there is no data for this word — it may be undecipherable or simply not Aramaic</div>"
        "<div>opaque extra summary</div>"
        "</body></html>"
    )
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(
            _response(
                body,
                url="https://cal.huc.edu/getlex.php?coord=9999999999999&word=0",
            )
        )

