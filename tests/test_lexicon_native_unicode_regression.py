from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconLookupService, LexiconLookupStatus


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("query", "expected_prefix"),
    [
        ("מֶלֶךְ", "מֶלֶךְ"),
        ("ܡܲܠܟܵܐ", "ܡܲܠܟܵ"),
    ],
)
async def test_cal_native_pointed_unicode_keeps_legacy_single_browse_path(
    query: str,
    expected_prefix: str,
) -> None:
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/browseSKEYheaders.php",
            body=b"<html><body>No matching lexical entries were found</body></html>",
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 8, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        result = await LexiconLookupService(client).lookup(query)
    finally:
        await client.aclose()

    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert requests == [
        CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", f'"{expected_prefix}"'),),
        )
    ]
    assert result.provenance is not None
    assert result.provenance.original_query == query
    assert result.provenance.normalized_query == query
    assert result.provenance.cal_code_word_candidates == ()
    assert result.provenance.cal_code_query_candidates == ()
    assert result.provenance.browse_prefixes == (expected_prefix,)
    assert result.provenance.selected_cal_code_candidates == ()
