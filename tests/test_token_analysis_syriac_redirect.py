from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.token_analysis import (
    TokenAnalysisParseError,
    TokenAnalysisService,
    parse_token_analysis_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
CURRENT = FIXTURES / "token_analysis_syriac_redirect_current.html"
TARGUM_CURRENT = FIXTURES / "token_analysis_targum_lexlink_current.html"
LEGACY = FIXTURES / "token_analysis_single.html"
RETRIEVED_AT = datetime(2026, 9, 27, tzinfo=UTC)
URL = "https://cal.huc.edu/getlex.php?coord=620570101&word=1"


def _response(body: str, *, url: str = URL) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _current_body() -> str:
    return CURRENT.read_text(encoding="utf-8")


def test_current_syriac_redirect_preserves_source_and_linked_target() -> None:
    page = parse_token_analysis_page(_response(_current_body()))

    assert len(page.candidates) == 1
    candidate = page.candidates[0]
    assert candidate.analysis_label == ")syr noun sg. emphatic= )syr N --> )syr A"
    assert candidate.analyzed_lemma_key == ")syr N"
    assert candidate.lemma.lemma_key == ")syr A"
    assert candidate.lemma.headwords == ("ˀsyr",)
    assert candidate.lemma.pronunciation == "ˀăsīr"
    assert candidate.lemma.part_of_speech == "adj."
    assert candidate.lemma.gloss == "captured; forbidden"


def test_current_syriac_sense_outline_is_not_an_extra_candidate() -> None:
    page = parse_token_analysis_page(_response(_current_body()))
    assert len(page.candidates) == 1
    assert "OUT-OF-SCOPE-SENSE" not in page.candidates[0].analysis_label
    assert "OUT-OF-SCOPE-SENSE" not in page.candidates[0].lemma.gloss


def test_current_lexlink_requires_nonempty_analysis_label() -> None:
    body = _current_body()
    label = ")syr noun sg. emphatic= )syr N --> )syr A"
    assert label in body
    with pytest.raises(TokenAnalysisParseError, match="analysis label"):
        parse_token_analysis_page(_response(body.replace(label, "   ", 1)))


def test_current_explicit_redirect_must_match_researched_suffix() -> None:
    body = _current_body()
    redirect = ")syr N --> )syr A"
    assert redirect in body
    with pytest.raises(TokenAnalysisParseError, match="redirect"):
        parse_token_analysis_page(_response(body.replace(redirect, ")syr N --> )syrA", 1)))


def test_current_explicit_redirect_must_be_unique() -> None:
    body = _current_body()
    redirect = ")syr N --> )syr A"
    assert redirect in body
    mutated = body.replace(redirect, ")syr N --> )syr X --> )syr A", 1)
    with pytest.raises(TokenAnalysisParseError, match="redirect"):
        parse_token_analysis_page(_response(mutated))


def test_legacy_linked_candidate_has_no_separate_analyzed_key() -> None:
    page = parse_token_analysis_page(_response(LEGACY.read_text(encoding="utf-8")))
    assert len(page.candidates) == 1
    assert page.candidates[0].analyzed_lemma_key is None


def test_current_targum_lexlink_without_redirect_keeps_null_analyzed_key() -> None:
    page = parse_token_analysis_page(
        _response(
            TARGUM_CURRENT.read_text(encoding="utf-8"),
            url="https://cal.huc.edu/getlex.php?coord=5101801011&word=0",
        )
    )

    assert len(page.candidates) == 1
    candidate = page.candidates[0]
    assert candidate.analysis_label == "nbw)h noun sg. emphatic"
    assert candidate.analyzed_lemma_key is None
    assert candidate.lemma.lemma_key == "nbw)h N"
    assert candidate.lemma.headwords == ("nbwˀh", "nbwˀtˀ")
    assert candidate.lemma.part_of_speech == "n.f."
    assert candidate.lemma.gloss == "prophecy"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('class="lexlink"', 'class="other"'),
        (")syr N --> )syr A", ")syr N --> )syr N"),
        ("lemma=%29syr+A&cits=all", "lemma=%29syr+N&cits=all"),
        ("lemma=%29syr+A&cits=all", "lemma=%29syr+A"),
        ("lemma=%29syr+A&cits=all", "lemma=%29syr+A&cits=all&extra=1"),
        ("lemma=%29syr+A&cits=all", "lemma=%29syr+A&lemma=%29syr+A&cits=all"),
    ],
)
def test_current_syriac_redirect_mutations_fail_closed(old: str, new: str) -> None:
    body = _current_body()
    assert old in body
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(body.replace(old, new, 1)))


def test_current_syriac_repeated_lexlink_fails_closed() -> None:
    body = _current_body()
    anchor = (
        '<a class="lexlink" href="oneentry.php?lemma=%29syr+A&cits=all">'
        '<span class="lem">ˀsyr</span> (<span class="rom">ˀăsīr</span>) '
        '<pos>adj.</pos> <span class="mgP">captured; forbidden</a></span><br>'
    )
    assert anchor in body
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(body.replace(anchor, anchor + anchor, 1)))


def test_current_syriac_unclosed_candidate_table_fails_closed() -> None:
    body = _current_body()
    assert "</td></tr></table>" in body
    with pytest.raises(TokenAnalysisParseError):
        parse_token_analysis_page(_response(body.replace("</td></tr></table>", "", 1)))


class RecordingTransport:
    def __init__(self, response: CalResponse) -> None:
        self.response = response
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return self.response


@pytest.mark.anyio
async def test_service_serializes_both_redirect_keys() -> None:
    response = _response(_current_body())
    transport = RecordingTransport(response)
    result = await TokenAnalysisService(CalHttpClient(transport=transport)).analyze(
        "620570101",
        1,
    )

    [candidate] = result.to_dict()["candidates"]
    assert candidate["analysis_label"] == ")syr noun sg. emphatic= )syr N --> )syr A"
    assert candidate["analyzed_lemma_key"] == ")syr N"
    assert candidate["lemma"]["lemma_key"] == ")syr A"
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="getlex.php",
            params=(("coord", "620570101"), ("word", "1")),
        )
    ]
