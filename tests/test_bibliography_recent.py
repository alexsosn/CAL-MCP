"""Issue #39: one-request CAL recent-bibliography snapshot (reduced semantic fixtures).

Source: https://cal.huc.edu/getrecentbib.php, rendered 2026-11-04;
raw structural counts in 2026-10-10 bounded research runs (see research plan).
No full CAL bibliography page is stored.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime

import pytest
from mcp import Client

from cal_mcp.bibliography import (
    BibliographyParseError,
    BibliographyQueryKind,
    BibliographyService,
    parse_recent_bibliography_page,
)
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse

URL = "https://cal.huc.edu/getrecentbib.php"
RETRIEVED_AT = datetime(2026, 11, 4, 11, 0, tzinfo=UTC)
RECORDS = (
    '<div class="card">'
    "<p>Gzella, H., Aramaic: A History of the First World Language. 2021. "
    '<a href="/getbibsigla.php?myauthor=History">History</a></p>'
    "<p>Gzella, H., Aramaic: A History of the First World Language. 2021. "
    '<a href="/getbibsigla.php?myauthor=History">History</a></p>'
    '<p>Butts, A.M., "A Hebrew and Syriac title: לשון ܣܘܪܝܝܐ". 2025. '
    '<a href="/getbiblemma.php?myauthor=ktb+V">ktb V</a></p>'
    "</div>"
)


def _response(body: str, url: str = URL) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=url,
        body=body.encode("utf-8"),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _page(records: str = RECORDS, extra: str = "") -> str:
    return (
        "<html><head><title>CAL Bibliography output</title></head><body>"
        "<h1>CAL Recent Bibliography</h1><p>CAL BIBLIOGRAPHY SEARCH</p>"
        + records
        + extra
        + "</body></html>"
    )


def test_recent_snapshot_preserves_order_duplicates_unicode_and_link_metadata() -> None:
    result = parse_recent_bibliography_page(_response(_page()))

    assert result.heading == "CAL Recent Bibliography"
    assert len(result.records) == 3
    assert result.records[0] == result.records[1]
    assert "לשון ܣܘܪܝܝܐ" in result.records[2].citation
    assert [link.query_kind for link in result.records[2].links] == [BibliographyQueryKind.LEMMA]
    assert result.records[2].links[0].query_value == "ktb V"
    assert result.records[0].links[0].url == (
        "https://cal.huc.edu/getbibsigla.php?myauthor=History"
    )
    assert not hasattr(result.records[0], "year")


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><h1>CAL Bibliography for TADA</h1>" + RECORDS + "</body></html>",
        "<html><body><h1>CAL Recent Bibliography</h1>"
        "<h1>CAL Recent Bibliography</h1>" + RECORDS + "</body></html>",
        "<html><body><h1>CAL Recent Bibliography</h1></body></html>",
        _page(records='<div class="card"><p>Unclosed citation'),
        _page(
            records='<div class="card"><p>2025 '
            '<a href="https://external.example/entry">external</a></p></div>'
        ),
        _page(
            records='<div class="card"><p>2025 '
            '<a href="/getbiblemma.php?myauthor=a&amp;myauthor=b">bad</a></p></div>'
        ),
        _page(records='<div class="card"><p>NO data FOR recent ARE CURRENTLY STORED</p></div>'),
        _page(extra='<form action="/getrecentbib.php"><button>Next</button></form>'),
        _page(extra='<a href="?page=2" rel="next">Next page</a>'),
    ],
)
def test_recent_snapshot_does_not_return_partial_or_invented_empty_results(body: str) -> None:
    with pytest.raises(BibliographyParseError):
        parse_recent_bibliography_page(_response(body))


class RecordingTransport:
    def __init__(self, body: str) -> None:
        self.body = body
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return _response(self.body)


@pytest.mark.anyio
async def test_recent_snapshot_is_one_fixed_get_with_no_year_filter_and_real_provenance() -> None:
    transport = RecordingTransport(_page())
    service = BibliographyService(CalHttpClient(transport=transport))
    result = await service.recent()

    assert transport.requests == [CalRequest(method="GET", path="getrecentbib.php")]
    assert result.heading == "CAL Recent Bibliography"
    assert len(result.records) == 3
    assert result.provenance.source == "CAL"
    assert result.provenance.source_url == URL
    assert result.provenance.retrieved_at == RETRIEVED_AT
    assert result.provenance.operation == "bibliography_recent"
    assert result.provenance.original_query == ""
    assert result.provenance.submitted_query == ""
    assert result.to_dict()["records"][0] == result.to_dict()["records"][1]


@pytest.mark.anyio
async def test_public_recent_bibliography_tool_requires_no_arguments() -> None:
    server = importlib.import_module("cal_mcp.server")
    async with Client(server.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    schema = tools["cal_bibliography_recent"].input_schema
    assert schema.get("properties") == {}
    assert schema.get("required", []) == []
    assert all(name not in schema.get("properties", {}) for name in ("year", "page", "limit"))
