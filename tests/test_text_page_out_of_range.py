"""Issue #167: an out-of-range page is a caller error, not upstream drift.

CAL clamps an out-of-range page to its last page (live 2026-09-25: ``page=50`` of the
50-page BT Berakhot renders "Page 50 of 50"). See docs/research/issue-167-talmud-pagination.md.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp import Client

import cal_mcp.server as server_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalOutOfRangeError, PublicErrorKind, classify_public_tool_error
from cal_mcp.texts import TextPageResult, TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
LAST = FIXTURES / "text_page_bt_ber_last_current.html"
PAGE_2 = FIXTURES / "text_page_bt_ber_p2_current.html"
TEL_DAN = FIXTURES / "text_page_tel_dan.html"


def _transport_for(fixture: Path) -> Transport:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        query = "&".join(f"{name}={value}" for name, value in request.params)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/get_a_chapter.php?{query}",
            body=fixture.read_bytes(),
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )

    return transport


async def _page(page: int, fixture: Path = LAST, file_id: str = "71001") -> TextPageResult:
    client = CalHttpClient(transport=_transport_for(fixture))
    try:
        return await TextService(client).page(file_id, page=page)
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


Transport = Callable[[CalRequest, CalClientConfig], Awaitable[CalResponse]]


@pytest.mark.anyio
async def test_request_beyond_the_range_on_a_non_last_page_is_still_drift() -> None:
    # Only CAL's clamp to its own last page is a range error (#167 review).
    with pytest.raises(TextParseError, match="page number differs"):
        await _page(51, PAGE_2)


@pytest.mark.anyio
async def test_page_two_of_a_single_page_text_is_out_of_range() -> None:
    # CAL clamps page=1 of the one-page Tel Dan text to its only page, with no
    # pagination marker and no navigation (live 2026-09-25, #167 review).
    with pytest.raises(CalOutOfRangeError, match=r"page 2 is beyond the last page \(1\)"):
        await _page(2, TEL_DAN, "13250")


@pytest.mark.anyio
async def test_out_of_range_page_reaches_mcp_callers_as_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def client_factory() -> CalHttpClient:
        return CalHttpClient(
            config=CalClientConfig(max_retries=0, retry_backoff_seconds=0),
            transport=_transport_for(LAST),
        )

    monkeypatch.setattr(server_module, "CalHttpClient", client_factory)
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool("cal_text_page", {"file_id": "71001", "page": 51})

    assert result.is_error is True
    assert result.structured_content == {
        "error": {
            "kind": "invalid_input",
            "operation": "cal_text_page",
            "upstream_reached": True,
            "retryable": False,
            "message": "page 51 is beyond the last page (50) of this text",
            "source_url": None,
            "status_code": None,
        }
    }


_PREVIOUS_LINK = (
    '<a href="get_a_chapter.php?file=71001&sub=&cset=R&clen=5&page=0">&laquo; previous page</a>'
)


def _without_markers(fixture: Path, *extra_removals: str) -> bytes:
    body = fixture.read_text(encoding="utf-8")
    body = re.sub(r"Page \d+ of \d+ &nbsp; (?:\(\d+ lines total\) &nbsp; )?", "", body)
    for text in extra_removals:
        assert text in body
        body = body.replace(text, "")
    assert re.search(r"Page \d+ of \d+", body) is None
    return body.encode()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("body", "page"),
    [
        # Both previous and next navigation remain.
        pytest.param(_without_markers(PAGE_2), 2, id="previous-and-next"),
        pytest.param(_without_markers(PAGE_2), 3, id="previous-and-next-page-3"),
        # Only previous navigation remains (a last page).
        pytest.param(_without_markers(LAST), 2, id="previous-only"),
        # Only next navigation remains.
        pytest.param(_without_markers(PAGE_2, _PREVIOUS_LINK), 2, id="next-only"),
    ],
)
async def test_paginated_page_that_lost_its_markers_but_keeps_navigation_is_drift(
    body: bytes, page: int
) -> None:
    # Only a page with no marker and no navigation is a one-page text (#167 review).
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config, request
        return CalResponse(
            status_code=200,
            url="https://cal.huc.edu/get_a_chapter.php?file=71001",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )

    client = CalHttpClient(transport=transport)
    try:
        with pytest.raises(TextParseError, match="page number differs"):
            await TextService(client).page("71001", page=page)
    finally:
        await client.aclose()
