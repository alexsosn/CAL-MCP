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


def _fixture_response(name: str, url: str = "https://cal.huc.edu/getlex.php") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=(FIXTURES / name).read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )


def test_single_token_analysis_preserves_cal_label_and_shared_lemma_ref() -> None:
    page = parse_token_analysis_page(_fixture_response("token_analysis_single.html"))

    assert len(page.candidates) == 1
    candidate = page.candidates[0]
    assert candidate.analysis_label == "xd n02"
    assert candidate.lemma.lemma_key == "xd b"
    assert candidate.lemma.headwords == ("ḥd",)
    assert candidate.lemma.pronunciation == "ḥaḏ"
    assert candidate.lemma.part_of_speech == "num."
    assert candidate.lemma.gloss == "one"


def test_multiple_token_analyses_preserve_cal_order_without_ranking() -> None:
    page = parse_token_analysis_page(_fixture_response("token_analysis_multiple.html"))

    assert [(item.analysis_label, item.lemma.lemma_key) for item in page.candidates] == [
        ("w_ c", "w_ c"),
        ("my c", "my c"),
    ]
    assert page.candidates[0].lemma.gloss == "and, also"
    assert page.candidates[1].lemma.gloss == "interrogative particle"


@pytest.mark.parametrize(
    ("fixture", "headword"),
    [
        ("token_analysis_unicode.html", "ܚܕ"),
        ("token_analysis_hebrew.html", "חד"),
    ],
)
def test_token_analysis_preserves_unicode_headword_display(fixture: str, headword: str) -> None:
    page = parse_token_analysis_page(_fixture_response(fixture))

    assert page.candidates[0].lemma.headwords == (headword,)


def test_explicit_cal_no_data_is_recognized_empty_analysis_page() -> None:
    page = parse_token_analysis_page(_fixture_response("token_analysis_not_found.html"))

    assert page.candidates == ()


@pytest.mark.parametrize(
    "body",
    [
        (FIXTURES / "token_analysis_marker_only.html").read_bytes(),
        (FIXTURES / "token_analysis_missing_lemma.html").read_bytes(),
        (
            b"<html><body>"
            b"<div>Click on a headword to see a complete lexicon entry</div>"
            b"<div>xd n02</div>"
            b'<div><a href="oneentry.php?cits=all">hd num. one</a></div>'
            b"</body></html>"
        ),
        b"<html><body>changed upstream markup</body></html>",
    ],
)
def test_unexplained_or_incomplete_success_page_is_parser_drift(body: bytes) -> None:
    response = CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getlex.php?coord=7102601002203&word=0",
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )

    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(response)


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_service_uses_one_exact_request_and_preserves_provenance() -> None:
    response = _fixture_response(
        "token_analysis_multiple.html",
        "https://cal.huc.edu/getlex.php?coord=7102601002203&word=0",
    )
    transport = RecordingTransport(response)
    service = TokenAnalysisService(CalHttpClient(transport=transport))

    result = await service.analyze("7102601002203", 0)

    assert result.status is TokenAnalysisStatus.FOUND
    assert [item.lemma.lemma_key for item in result.candidates] == ["w_ c", "my c"]
    assert result.provenance.coordinate == "7102601002203"
    assert result.provenance.word_index == 0
    assert result.provenance.source == "CAL"
    assert result.provenance.source_url == response.url
    assert result.provenance.retrieved_at == response.retrieved_at
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="getlex.php",
            params=(("coord", "7102601002203"), ("word", "0")),
        )
    ]

    structured = result.to_dict()
    assert structured["status"] == "found"
    assert structured["coordinate"] == "7102601002203"
    assert structured["word_index"] == 0


@pytest.mark.anyio
async def test_service_maps_explicit_no_data_to_not_found() -> None:
    response = _fixture_response(
        "token_analysis_not_found.html",
        "https://cal.huc.edu/getlex.php?coord=9999999999999&word=0",
    )
    transport = RecordingTransport(response)
    service = TokenAnalysisService(CalHttpClient(transport=transport))

    result = await service.analyze("9999999999999", 0)

    assert result.status is TokenAnalysisStatus.NOT_FOUND
    assert result.candidates == ()
    assert len(transport.requests) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("coordinate", "word_index"),
    [
        ("", 0),
        ("abc", 0),
        ("12 3", 0),
        ("123", -1),
        ("123", True),
    ],
)
async def test_invalid_token_request_fails_before_transport(
    coordinate: str,
    word_index: int,
) -> None:
    transport = RecordingTransport(_fixture_response("token_analysis_single.html"))
    service = TokenAnalysisService(CalHttpClient(transport=transport))

    with pytest.raises(ValueError):
        await service.analyze(coordinate, word_index)

    assert transport.requests == []
