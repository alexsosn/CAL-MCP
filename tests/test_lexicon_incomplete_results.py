"""Issue #277: do not claim a full CAL lexicon miss from a truncated browse page."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LemmaRef,
    LexiconLookupService,
    LexiconParseError,
    _browse_prefix,
    _query_matches,
    parse_browse_page,
)

STAMP = datetime(2026, 10, 10, tzinfo=UTC)
CURSOR = "bjw@ bnjn b"
PAGE = (
    "<html><body>"
    '<div><a href="/oneentry.php?cits=all&amp;lemma=byt+N">byt n.m. house</a></div>'
    "<div>house</div>"
    '<a href="browseSKEYheaders.php?direction=1&amp;sortkey=bjw%40%20bnjn%20b">'
    "NEXT PAGE</a>"
    "</body></html>"
)


def response(body: str = PAGE, *, prefix: str = "byt") -> CalResponse:
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/browseSKEYheaders.php?first3=%22{prefix}%22",
        body=body.encode("utf-8"),
        content_type="text/html",
        retrieved_at=STAMP,
    )


def test_lookup_parser_exposes_existing_cal_browse_cursor() -> None:
    page = parse_browse_page(response())
    assert [row.lemma_key for row in page.entries] == ["byt N"]
    assert page.next_continuation == CURSOR


@pytest.mark.parametrize(
    "bad",
    [
        "https://evil.example/browseSKEYheaders.php?direction=1&sortkey=br",
        "browseSKEYheaders.php?direction=2&sortkey=br",
        "browseSKEYheaders.php?direction=1&sortkey=br&extra=1",
        "browseSKEYheaders.php?direction=1&sortkey=br#fragment",
        "oneentry.php?direction=1&sortkey=br",
    ],
)
def test_lookup_parser_rejects_unsafe_continuation_links(bad: str) -> None:
    mutated = PAGE.replace(
        "browseSKEYheaders.php?direction=1&amp;sortkey=bjw%40%20bnjn%20b",
        bad.replace("&", "&amp;"),
    )
    with pytest.raises(LexiconParseError):
        parse_browse_page(response(mutated))


def test_lookup_parser_rejects_duplicate_browse_next_links() -> None:
    duplicated = PAGE.replace(
        "</body>",
        '<a href="browseSKEYheaders.php?direction=1&amp;sortkey=br">NEXT PAGE</a></body>',
    )
    with pytest.raises(LexiconParseError):
        parse_browse_page(response(duplicated))


@pytest.mark.anyio
async def test_missing_lemma_on_page_with_next_is_truncated_without_extra_get() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return response()

    service = LexiconLookupService(CalHttpClient(transport=transport))
    result = await service.lookup("byt mlkw")
    payload = result.to_dict()
    assert payload["status"] == "truncated"
    assert payload["matches"] == []
    assert payload["entry"] is None
    assert payload["browse_truncated"] is True
    assert payload["browse_continuations"] == [{"prefix": "byt", "continuation": CURSOR}]
    assert payload["provenance"]["source"] == "CAL"
    assert requests == [
        CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", '"byt"'),),
        )
    ]


@pytest.mark.anyio
async def test_complete_browse_no_match_remains_actual_not_found() -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        html = PAGE.split('<a href="browseSKEYheaders.php?direction=1')[0]
        return response(html + "</body></html>")

    result = await LexiconLookupService(CalHttpClient(transport=transport)).lookup("byt mlkw")
    payload = result.to_dict()
    assert payload["status"] == "not_found"
    assert payload["browse_truncated"] is False
    assert payload["browse_continuations"] == []
    assert len(requests) == 1


def test_machine_cal_at_separator_is_not_a_third_consonant() -> None:
    assert _browse_prefix("xd@(sr") == "xd"
    assert _browse_prefix("byt mlkw") == "byt"


def test_machine_multiword_lemma_is_exact_match_for_cal_or_split_word_input() -> None:
    candidate = LemmaRef(
        lemma_key="xd@(sr b",
        headwords=("ḥədˁesrē",),
        pronunciation=None,
        part_of_speech="num.",
        gloss="eleven",
    )
    assert _query_matches("xd@(sr", candidate)
    palace = LemmaRef(
        lemma_key="byt@mlkw N",
        headwords=("bēṯ malkā",),
        pronunciation=None,
        part_of_speech="n.m.",
        gloss="palace",
    )
    assert _query_matches("byt mlkw", palace)
    assert not _query_matches("byt mlk", palace)
