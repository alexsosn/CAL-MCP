"""Issue #167: an out-of-range page is a caller error, not upstream drift.

CAL clamps an out-of-range page to its last page (live 2026-09-25: ``page=50`` of the
50-page BT Berakhot renders "Page 50 of 50"). See docs/research/issue-167-talmud-pagination.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalOutOfRangeError, PublicErrorKind, classify_public_tool_error
from cal_mcp.texts import TextPageResult, TextParseError, TextService

LAST = Path(__file__).parent / "fixtures" / "cal" / "text_page_bt_ber_last_current.html"


async def _transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
    del config
    query = "&".join(f"{name}={value}" for name, value in request.params)
    return CalResponse(
        status_code=200,
        url=f"https://cal.huc.edu/get_a_chapter.php?{query}",
        body=LAST.read_bytes(),
        content_type="text/html; charset=UTF-8",
        retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
    )


async def _page(page: int) -> TextPageResult:
    client = CalHttpClient(transport=_transport)
    try:
        return await TextService(client).page("71001", page=page)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_page_beyond_the_last_page_is_an_input_error_naming_the_range() -> None:
    with pytest.raises(CalOutOfRangeError, match=r"page 51 is beyond the last page \(50\)"):
        await _page(51)


@pytest.mark.anyio
async def test_page_mismatch_inside_the_range_is_still_drift() -> None:
    with pytest.raises(TextParseError, match="page number differs"):
        await _page(3)


def test_out_of_range_error_is_public_invalid_input_that_reached_cal() -> None:
    error = classify_public_tool_error("cal_text_page", CalOutOfRangeError("page 51 is beyond"))

    assert error is not None
    assert error.kind is PublicErrorKind.INVALID_INPUT
    assert error.upstream_reached is True
    assert error.retryable is False
