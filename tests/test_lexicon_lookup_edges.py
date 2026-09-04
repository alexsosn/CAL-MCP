from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import LexiconLookupService, LexiconLookupStatus

FIXTURES = Path(__file__).parent / "fixtures" / "cal"


class BrowseOnlyTransport:
    def __init__(self) -> None:
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/browseSKEYheaders.php",
            body=(FIXTURES / "browse_b.html").read_bytes(),
            content_type="text/html",
            retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        )


@pytest.mark.anyio
async def test_multiword_browser_prefix_preserves_space_equivalent_of_cal_at_sign() -> None:
    transport = BrowseOnlyTransport()
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup("br@mwt)")

    assert result.status is LexiconLookupStatus.NOT_FOUND
    assert transport.requests == [
        CalRequest(
            method="GET",
            path="browseSKEYheaders.php",
            params=(("first3", '"br "'),),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["בר", "ܒܪ"])
async def test_hebrew_and_syriac_headwords_match_same_cal_candidates(query: str) -> None:
    transport = BrowseOnlyTransport()
    service = LexiconLookupService(CalHttpClient(transport=transport))

    result = await service.lookup(query)

    assert result.status is LexiconLookupStatus.AMBIGUOUS
    assert [item.lemma_key for item in result.matches] == ["br N", "br#2 N"]
    assert len(transport.requests) == 1
