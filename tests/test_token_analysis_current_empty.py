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

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "token_analysis_current_no_lemma.html"


def _response(body: bytes | None = None) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getlex.php?coord=1325007&word=1",
        body=FIXTURE.read_bytes() if body is None else body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
    )


def test_current_cal_no_lemma_state_is_recognized_as_empty_analysis() -> None:
    page = parse_token_analysis_page(_response())

    assert page.candidates == ()


class RecordingTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return _response()


@pytest.mark.anyio
async def test_service_maps_current_no_lemma_state_to_not_found_in_one_request() -> None:
    transport = RecordingTransport()
    client = CalHttpClient(transport=transport)
    try:
        result = await TokenAnalysisService(client).analyze("1325007", 1)
    finally:
        await client.aclose()

    assert result.status is TokenAnalysisStatus.NOT_FOUND
    assert result.coordinate == "1325007"
    assert result.word_index == 1
    assert result.candidates == ()
    assert result.provenance.coordinate == "1325007"
    assert result.provenance.word_index == 1
    assert result.provenance.source == "CAL"
    assert result.provenance.source_url == _response().url
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="getlex.php",
            params=(("coord", "1325007"), ("word", "1")),
        )
    ]


def test_current_no_lemma_state_mixed_with_lemma_link_fails_closed() -> None:
    body = b"".join(
        [
            b"<html><body>",
            b"<div>Click on a headword to see a complete lexicon entry</div>",
            b'<div>| W.D. "unrecognizable query or no such lemma found"</div>',
            b'<div><a href="oneentry.php?lemma=xd+b&amp;cits=all">',
            "ḥd (ḥaḏ) num. one".encode(),
            b"</a></div>",
            b'<div><a href="/newtextmenu.html">Return to the Text Browser</a></div>',
            b"</body></html>",
        ]
    )

    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(body))


def test_current_no_lemma_state_without_analysis_marker_fails_closed() -> None:
    body = (
        b"<html><body>"
        b'<div>| W.D. "unrecognizable query or no such lemma found"</div>'
        b'<div><a href="/newtextmenu.html">Return to the Text Browser</a></div>'
        b"</body></html>"
    )

    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(body))
