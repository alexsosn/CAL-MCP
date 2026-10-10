"""Issue #259: CAL text search rejects or silently rewrites some query characters.

CAL echoes the term it actually searched. A rewritten term must never be returned as the result
for the caller's original query (R-077).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalRejectedInputError
from cal_mcp.texts import TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
REJECTED = FIXTURES / "text_search_rejected_non_ascii_current.html"
STRIPPED = FIXTURES / "text_search_stripped_echo_current.html"
TEL_DAN = FIXTURES / "text_search_tel_dan.html"


async def _search(query: str, body: bytes):
    requests: list[CalRequest] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        requests.append(request)
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/newsearchtxts.php",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        return await TextService(client).search(query), requests
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_cal_rejection_of_a_non_ascii_query_is_typed_rejected_input() -> None:
    with pytest.raises(CalRejectedInputError, match='CAL rejected the text search: ""'):
        await _search("מלכא", REJECTED.read_bytes())


@pytest.mark.anyio
async def test_cal_searching_a_rewritten_term_is_not_returned_for_the_original_query() -> None:
    with pytest.raises(CalRejectedInputError) as caught:
        await _search("Aḥiqar", STRIPPED.read_bytes())

    message = str(caught.value)
    assert '"Aiqar"' in message
    assert '"Aḥiqar"' in message


@pytest.mark.anyio
async def test_matching_echo_still_returns_cal_results() -> None:
    result, requests = await _search("Tel Dan", TEL_DAN.read_bytes())

    assert [match.file_id for match in result.matches] == ["13250"]
    assert len(requests) == 1


@pytest.mark.anyio
async def test_matching_echo_on_an_empty_result_is_an_ordinary_empty_result() -> None:
    result, _ = await _search("Aiqar", STRIPPED.read_bytes())

    assert result.matches == ()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # The no-files marker names a different term than the heading.
        (b"search term Aiqar</p>", b"search term Ahiqar</p>"),
        # Two different echoed headings.
        (
            b"</h3>",
            b"</h3><h3>CAL search for texts like: Other. Click on the file number to view.</h3>",
        ),
    ],
)
async def test_contradictory_echoes_are_parser_drift(old: bytes, new: bytes) -> None:
    body = STRIPPED.read_bytes()
    assert old in body

    with pytest.raises(TextParseError):
        await _search("Aiqar", body.replace(old, new))


@pytest.mark.anyio
async def test_rejection_beside_results_is_parser_drift() -> None:
    body = TEL_DAN.read_bytes().replace(
        b"</body>", b'<div>"" is not a valid search string</div></body>'
    )

    with pytest.raises(TextParseError):
        await _search("Tel Dan", body)


@pytest.mark.anyio
async def test_repeated_heading_on_a_results_page_is_parser_drift() -> None:
    # No no-files marker here, so only the duplicate-heading guard can catch it.
    body = TEL_DAN.read_bytes().replace(
        b"</body>",
        b"<div>CAL search for texts like: Tel Dan. Click on the file number to view.</div></body>",
    )

    with pytest.raises(TextParseError, match="repeats"):
        await _search("Tel Dan", body)
