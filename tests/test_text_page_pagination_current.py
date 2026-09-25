"""Issue #167: current (2026-09-25) pagination marker on paginated text pages.

See docs/research/issue-167-talmud-pagination.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.texts import TextPageResult, TextParseError, TextService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
PAGE_2 = FIXTURES / "text_page_bt_ber_p2_current.html"
LAST = FIXTURES / "text_page_bt_ber_last_current.html"


class FixtureTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        query = "&".join(f"{name}={value}" for name, value in request.params)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/get_a_chapter.php?{query}",
            body=self.body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


async def _page(body: bytes, page: int) -> TextPageResult:
    client = CalHttpClient(transport=FixtureTransport(body))
    try:
        return await TextService(client).page("71001", page=page)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_current_middle_page_reports_pagination_and_navigation() -> None:
    result = await _page(PAGE_2.read_bytes(), 2)

    assert result.page is not None
    assert result.page.text.label == "BT Ber"
    assert (result.page.page, result.page.page_count, result.page.total_lines) == (2, 50, 2251)
    assert (result.page.previous_page, result.page.next_page) == (1, 3)
    assert len(result.page.lines) == 2


@pytest.mark.anyio
async def test_current_last_page_reports_pagination_without_next() -> None:
    result = await _page(LAST.read_bytes(), 50)

    assert result.page is not None
    assert (result.page.page, result.page.page_count, result.page.total_lines) == (50, 50, 2251)
    assert (result.page.previous_page, result.page.next_page) == (49, None)


_TOP = "Page 2 of 50 &nbsp; (2251 lines total) &nbsp; "
_BOTTOM = "Page 2 of 50 &nbsp; <a"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        # The two markers disagree on the page.
        (_BOTTOM, "Page 3 of 50 &nbsp; <a", "conflicting pagination metadata"),
        # The two markers disagree on the page count.
        (_BOTTOM, "Page 2 of 51 &nbsp; <a", "conflicting pagination metadata"),
        # A second marker reports a different line total.
        (_BOTTOM, "Page 2 of 50 &nbsp; (2250 lines total) &nbsp; <a", "conflicting"),
        # Stray text next to a marker is a malformed marker, not a silently skipped line.
        (
            _TOP,
            "Page 2 of 50 &nbsp; (2251 lines total) extra &nbsp; ",
            "malformed pagination marker",
        ),
    ],
)
async def test_inconsistent_or_unrecognized_markers_fail_closed(
    old: str, new: str, message: str
) -> None:
    body = PAGE_2.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(TextParseError, match=message):
        await _page(body.replace(old, new, 1).encode(), 2)


@pytest.mark.anyio
async def test_navigation_without_any_recognizable_marker_fails_closed() -> None:
    body = (
        PAGE_2.read_text(encoding="utf-8")
        .replace(_TOP, "Seite 2 von 50 ", 1)
        .replace(_BOTTOM, "Seite 2 von 50 <a", 1)
    )
    with pytest.raises(
        TextParseError, match="navigation without pagination metadata|page number differs"
    ):
        await _page(body.encode(), 2)


@pytest.mark.anyio
async def test_marker_text_inside_a_token_line_is_not_a_marker() -> None:
    # Only non-token lines can carry the pagination marker.
    body = PAGE_2.read_text(encoding="utf-8").replace(_TOP, "", 1).replace(_BOTTOM, "<a", 1)
    first_row_end = body.index("</td></tr>")
    body = body[:first_row_end] + " Page 2 of 50" + body[first_row_end:]
    with pytest.raises(
        TextParseError, match="navigation without pagination metadata|page number differs"
    ):
        await _page(body.encode(), 2)
