from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconLookupService, LexiconLookupStatus, parse_lexicon_entry

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


def _response(html: str, *, lemma_key: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/cal_entry_web.php?lemma={lemma_key}",
        body=html.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("header", "expected_pos"),
    [
        ("hˀ interj. behold", "interj."),
        ("hāḵēl adv./conj. now, now then", "adv./conj."),
    ],
)
def test_current_cal_pos_tokens_are_not_rejected_by_a_closed_whitelist(
    header: str,
    expected_pos: str,
) -> None:
    entry = parse_lexicon_entry(
        _response(
            f"<html><body><header>{header}</header>"
            "<div>definition</div><div>Common Aramaic</div></body></html>",
            lemma_key="test X",
        ),
        lemma_key="test X",
    )

    assert entry.lemma.part_of_speech == expected_pos


def test_hyphenated_cal_dialect_labels_are_preserved_as_dialects() -> None:
    entry = parse_lexicon_entry(
        _response(
            "<html><body><header>test n.m. thing</header>"
            "<div>1</div><div>definition</div>"
            "<div>OfA-Egypt, OfA-Pers, OfA-West</div>"
            "</body></html>",
            lemma_key="test N",
        ),
        lemma_key="test N",
    )

    assert entry.senses[0].definition == "definition"
    assert entry.senses[0].dialects == ("OfA-Egypt", "OfA-Pers", "OfA-West")


def test_mixed_plain_and_linked_citations_are_preserved_in_order() -> None:
    entry = parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
            body=(FIXTURES / "entry_br_nested.html").read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        ),
        lemma_key="br N",
    )

    citations = entry.senses[1].citations
    assert len(citations) == 4
    assert [(item.reference, item.url, item.text) for item in citations] == [
        (None, None, "EphCruc 2:3 ܐܝܟܢܐ raw-one"),
        (None, None, "EphNis 41:12 ܐܡܪ raw-two"),
        (
            "IshDan 106(17)",
            "https://cal.huc.edu/citation.php?id=ishdan-106-17",
            "linked-three",
        ),
        (
            "BT Tan 22a(25)",
            "https://cal.huc.edu/citation.php?id=bt-tan-22a-25",
            "linked-four",
        ),
    ]


class ScriptBrowseTransport:
    def __init__(self, headword: str) -> None:
        self._headword = headword
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        html = (
            "<html><body>"
            f'<div><a href="/oneentry.php?lemma=test1+N">{self._headword} n.m.</a></div>'
            "<div>one</div>"
            f'<div><a href="/oneentry.php?lemma=test2+N">{self._headword} n.f.</a></div>'
            "<div>two</div>"
            "</body></html>"
        )
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/browseSKEYheaders.php",
            body=html.encode(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("query", "browser_headword"),
    [
        ("שׂר", "śr"),
        ("ܧܪ", "ṗr"),
    ],
)
async def test_documented_script_consonants_match_browser_unicode_headwords(
    query: str,
    browser_headword: str,
) -> None:
    transport = ScriptBrowseTransport(browser_headword)
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup(query)

    assert result.status is LexiconLookupStatus.AMBIGUOUS
    assert [item.lemma_key for item in result.matches] == ["test1 N", "test2 N"]
    assert len(transport.requests) == 1
