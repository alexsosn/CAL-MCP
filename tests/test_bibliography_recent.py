from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client

import cal_mcp.bibliography as bibliography
from cal_mcp.bibliography import BibliographyParseError, BibliographyQueryKind, BibliographyService
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
RETRIEVED_AT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def _fixture_response() -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getrecentbib.php",
        body=(FIXTURES / "bibliography_recent_current.html").read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _inline_response(body: str) -> CalResponse:
    return CalResponse(
        status_code=200,
        url="https://cal.huc.edu/getrecentbib.php",
        body=body.encode(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=RETRIEVED_AT,
    )


def _recent_parser() -> Callable[[CalResponse], Any]:
    parser = getattr(bibliography, "parse_recent_bibliography_page", None)
    assert callable(parser)
    return cast(Callable[[CalResponse], Any], parser)


def test_recent_parser_preserves_order_duplicates_and_existing_link_semantics() -> None:
    page = _recent_parser()(_fixture_response())

    assert page.heading == "CAL Recent Bibliography"
    assert len(page.records) == 4
    assert "2010–2015" in page.records[1].citation
    assert page.records[2].citation == page.records[3].citation
    assert not hasattr(page, "years")

    first_link = page.records[0].links[0]
    assert first_link.query_kind is BibliographyQueryKind.KEYWORD
    assert first_link.query_value == "history"

    lemma_link = page.records[2].links[0]
    assert lemma_link.query_kind is BibliographyQueryKind.LEMMA
    assert lemma_link.query_value == "(dn N"


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><h1>CAL Recent Bibliography</h1></body></html>",
        (
            "<html><body><h1>CAL Bibliography</h1>"
            '<div class="card">Citation, 2025.</div></body></html>'
        ),
        (
            "<html><body><h1>CAL Recent Bibliography</h1>"
            "<h1>CAL Recent Bibliography</h1>"
            '<div class="card">Citation, 2025.</div></body></html>'
        ),
        (
            "<html><body><h1>CAL Recent Bibliography</h1>"
            '<div class="card">Citation, 2025. '
            '<a href="https://example.org/x">outside</a></div></body></html>'
        ),
    ],
)
def test_recent_parser_fails_closed_on_missing_semantics_or_unsafe_links(body: str) -> None:
    with pytest.raises(BibliographyParseError):
        _recent_parser()(_inline_response(body))


class RecordingTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        assert request.path == "getrecentbib.php"
        return _fixture_response()


@pytest.mark.anyio
async def test_recent_service_is_one_parameterless_request_with_null_query_provenance() -> None:
    transport = RecordingTransport()
    service = BibliographyService(CalHttpClient(transport=transport))
    recent = getattr(service, "recent", None)
    assert callable(recent)

    result = await recent()

    assert transport.requests == [CalRequest(method="GET", path="getrecentbib.php")]
    assert result.heading == "CAL Recent Bibliography"
    assert result.records[2].citation == result.records[3].citation
    assert result.provenance.operation == "bibliography_recent"
    assert result.provenance.original_query is None
    assert result.provenance.submitted_query is None

    payload = result.to_dict()
    assert set(payload) == {"heading", "records", "provenance"}
    assert "years" not in payload
    provenance = cast(dict[str, object], payload["provenance"])
    assert provenance["original_query"] is None
    assert provenance["submitted_query"] is None


@pytest.mark.anyio
async def test_recent_bibliography_mcp_schema_is_parameterless() -> None:
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert "cal_bibliography_recent" in tools
    schema = tools["cal_bibliography_recent"].input_schema
    assert set(schema["properties"]) == set()
    assert "required" not in schema or schema["required"] == []
