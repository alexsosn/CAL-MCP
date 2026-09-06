from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import (
    LexiconLookupService,
    LexiconLookupStatus,
    LexiconParseError,
    parse_lexicon_entry,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


class Issue41Transport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        if request.path == "browseSKEYheaders.php":
            body = (FIXTURES / "browse_b.html").read_bytes()
            url = "https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22"
        elif request.path == "cal_entry_web.php":
            body = (FIXTURES / "entry_br_current_citations.html").read_bytes()
            url = "https://cal.huc.edu/cal_entry_web.php?lemma=br+N"
        else:
            raise AssertionError(f"unexpected CAL request: {request}")
        return CalResponse(
            status_code=200,
            url=url,
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 6, tzinfo=UTC),
        )


@pytest.mark.anyio
async def test_current_structural_citations_preserve_three_items_without_hidden_variants() -> None:
    transport = Issue41Transport()
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup("br", lemma_key="br N")

    assert result.status is LexiconLookupStatus.FOUND
    assert result.entry is not None
    citations = result.entry.senses[0].citations
    assert [(item.reference, item.url, item.text) for item in citations] == [
        ("EphCruc 2:3", None, "ܐܝܟܢܐ ܢܪܫܘܡ : visible first"),
        (
            "IshDan 106(17)",
            "https://cal.huc.edu/showachapter.php?fullcoord=ishdan-example",
            "visible second",
        ),
        (
            "BT Yev 76a(40)",
            "https://cal.huc.edu/showachapter.php?fullcoord=7101301076140",
            "וכי גזרו בהו רבנן : children; the rabbis did not decree it",
        ),
    ]
    assert all("hidden" not in item.text for item in citations)
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", '"br"'),),
        ),
        CalRequest(
            method="GET",
            path="cal_entry_web.php",
            params=(("lemma", "br N"),),
        ),
    ]


# Review 5125438201: HTMLParser emits start and end callbacks for a self-closing <br/>.
def test_hidden_alternate_citation_script_allows_self_closing_void_element() -> None:
    html = (FIXTURES / "entry_br_current_citations.html").read_text(encoding="utf-8")
    html = html.replace("hidden; alternate", "hidden<br/>alternate", 1)

    entry = parse_lexicon_entry(
        CalResponse(
            status_code=200,
            url="https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
            body=html.encode(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 6, tzinfo=UTC),
        ),
        lemma_key="br N",
    )

    citations = entry.senses[0].citations
    assert len(citations) == 3
    assert all("hidden" not in item.text and "alternate" not in item.text for item in citations)


def test_current_structural_citations_still_fail_closed_on_wrong_rendered_count() -> None:
    html = (FIXTURES / "entry_br_current_citations.html").read_text(encoding="utf-8")
    html = html.replace("3 citations", "4 citations", 1)

    with pytest.raises(LexiconParseError, match="citation count"):
        parse_lexicon_entry(
            CalResponse(
                status_code=200,
                url="https://cal.huc.edu/cal_entry_web.php?lemma=br+N",
                body=html.encode(),
                content_type="text/html; charset=UTF-8",
                retrieved_at=datetime(2026, 9, 6, tzinfo=UTC),
            ),
            lemma_key="br N",
        )
