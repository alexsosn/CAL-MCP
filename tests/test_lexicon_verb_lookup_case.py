from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LemmaRef, LexiconLookupService, _query_matches

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _client() -> CalHttpClient:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        assert request.path == "browseSKEYheaders.php"
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/browseSKEYheaders.php",
            body=(FIXTURES / "browse_verb_vowel_class.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 9, tzinfo=UTC),
        )

    return CalHttpClient(
        config=CalClientConfig(max_retries=0, retry_backoff_seconds=0), transport=transport
    )


@pytest.mark.anyio
async def test_lookup_offers_the_verb_whose_root_cal_shows_in_uppercase() -> None:
    result = await LexiconLookupService(_client()).lookup("(hr")

    assert result.status.value == "ambiguous"
    assert [item.lemma_key for item in result.matches] == ["(hr V", "(hr A"]
    # CAL's displayed headwords are kept as rendered.
    assert result.matches[0].headwords == ("ˁHR", "ˀHR")


def _lemma(key: str, *headwords: str) -> LemmaRef:
    return LemmaRef(
        lemma_key=key, headwords=headwords, pronunciation=None, part_of_speech=None, gloss=""
    )


def test_case_is_folded_only_for_uppercase_verb_roots() -> None:
    assert _query_matches("ktb", _lemma("ktb V", "KTB"))
    # A non-verb headword keeps its case-significant comparison.
    assert not _query_matches("qmpy", _lemma("qmPyh N", "qmPy"))
    # A verb headword that is not entirely uppercase is not folded.
    assert not _query_matches("ktb", _lemma("ktb V", "Ktb"))

@pytest.mark.parametrize("query", ["ktb", "כתב"])
def test_lowercase_cal_and_hebrew_query_match_uppercase_verb_root(query: str) -> None:
    assert _query_matches(query, _lemma("ktb V", "KTB"))


def test_exact_verb_root_display_is_preserved_without_folding_other_pos() -> None:
    assert _query_matches("ˁhr", _lemma("(hr V", "ˁHR", "ˀHR"))
    assert not _query_matches("ˁhr", _lemma("(hr A", "ˁHR"))
    assert not _query_matches("tm", _lemma("Tm N", "Tm"))

