"""Issue #207: CAL's explicit "is not a valid search string" citation-search rejection.

See docs/research/issue-207-invalid-search-string.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp import Client

import cal_mcp.server as server_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import (
    CalOutOfRangeError,
    CalRejectedInputError,
    PublicErrorKind,
    classify_public_tool_error,
)
from cal_mcp.search import SearchParseError, parse_citation_search_page

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "search_citations_invalid_god_current.html"
URL = "https://cal.huc.edu/searchcits.php"


def _response(body: bytes) -> CalResponse:
    return CalResponse(
        status_code=200,
        url=URL,
        body=body,
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 29, tzinfo=UTC),
    )


def test_cal_rejection_of_the_submitted_query_is_rejected_input() -> None:
    with pytest.raises(CalRejectedInputError, match='"god" is not a valid search string'):
        parse_citation_search_page(_response(FIXTURE.read_bytes()), submitted_query="god")


@pytest.mark.parametrize("submitted", ["king", None])
def test_rejection_quoting_another_or_unknown_query_fails_closed(submitted: str | None) -> None:
    with pytest.raises(SearchParseError):
        parse_citation_search_page(_response(FIXTURE.read_bytes()), submitted_query=submitted)


def test_out_of_range_is_still_classified_as_invalid_input_that_reached_cal() -> None:
    assert issubclass(CalOutOfRangeError, CalRejectedInputError)
    error = classify_public_tool_error("cal_text_page", CalOutOfRangeError("page 9 is beyond"))

    assert error is not None
    assert error.kind is PublicErrorKind.INVALID_INPUT
    assert error.upstream_reached is True


@pytest.mark.anyio
async def test_rejection_reaches_mcp_callers_as_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del request, config
        return _response(FIXTURE.read_bytes())

    def client_factory() -> CalHttpClient:
        return CalHttpClient(
            config=CalClientConfig(max_retries=0, retry_backoff_seconds=0),
            transport=transport,
        )

    monkeypatch.setattr(server_module, "CalHttpClient", client_factory)
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_citation_text_search", {"query": "god"})

    assert result.is_error is True
    assert result.structured_content == {
        "error": {
            "kind": "invalid_input",
            "operation": "cal_citation_text_search",
            "upstream_reached": True,
            "retryable": False,
            "message": 'CAL rejected the citation search: "god" is not a valid search string',
            "source_url": None,
            "status_code": None,
        }
    }
