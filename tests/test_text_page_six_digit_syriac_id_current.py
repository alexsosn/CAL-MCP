"""Issue #186: six-digit Syriac text ids are CAL file plus subtext (634081 = 63408 + 1).

See docs/research/issue-186-six-digit-syriac-id.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalOutOfRangeError, CalParseError
from cal_mcp.texts import TextPageResult, TextPageStatus, TextService

FIXTURE = Path(__file__).parent / "fixtures" / "cal" / "text_page_634081_current.html"


class FixtureTransport:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        query = "&".join(f"{name}={value}" for name, value in request.params)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/get_a_chapter.php?{query}",
            body=self.body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


async def _page(
    body: bytes, file_id: str, page: int = 1
) -> tuple[TextPageResult, FixtureTransport]:
    transport = FixtureTransport(body)
    client = CalHttpClient(transport=transport)
    try:
        return await TextService(client).page(file_id, page=page), transport
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_six_digit_syriac_id_page_is_read_under_the_requested_id() -> None:
    result, transport = await _page(FIXTURE.read_bytes(), "634081")

    assert result.status is TextPageStatus.FOUND
    assert result.page is not None
    assert result.page.text.file_id == "634081"
    assert result.page.text.subtext_id is None
    assert result.page.text.label == "Tamar and Judah"
    assert [line.coordinate for line in result.page.lines] == ["634081001", "634081002"]
    assert (result.page.page, result.page.page_count, result.page.total_lines) == (1, 9, 420)
    assert (result.page.previous_page, result.page.next_page) == (None, 2)
    assert transport.requests[0].params == (("file", "634081"), ("page", "0"))


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # a label naming an unrelated file
        (b">63408: Tamar and Judah<", b">63409: Tamar and Judah<"),
        # a shorter prefix whose remainder is not CAL's linked sub
        (b">63408: Tamar and Judah<", b">6340: Tamar and Judah<"),
        # CAL's own links name another sub
        (b"file=63408&sub=1&", b"file=63408&sub=2&"),
        (b"file=63408&amp;sub=1&", b"file=63408&amp;sub=2&"),
    ],
)
async def test_split_label_without_matching_cal_links_fails_closed(old: bytes, new: bytes) -> None:
    body = FIXTURE.read_bytes()
    assert old in body
    body = body.replace(old, new)
    if old.startswith(b"file=63408&sub=1&"):
        body = body.replace(b"file=63408&amp;sub=1&", b"file=63408&amp;sub=2&")
    if old.startswith(b"file=63408&amp;sub=1&"):
        body = body.replace(b"file=63408&sub=1&", b"file=63408&sub=2&")

    with pytest.raises(CalParseError):
        await _page(body, "634081")


@pytest.mark.anyio
async def test_split_label_without_any_cal_page_links_fails_closed() -> None:
    body = FIXTURE.read_bytes().replace(b"get_a_chapter.php", b"other_page.php")

    with pytest.raises(CalParseError):
        await _page(body, "634081")


_NEXT = b'<a href="get_a_chapter.php?file=63408&sub=1&cset=R&clen=5&page=1">next page &raquo;'
_PREVIOUS = (
    b'<a href="get_a_chapter.php?file=63408&sub=1&cset=R&clen=5&page={}">&laquo; previous page'
)


def _as_page(page: int, *, last: bool = False) -> bytes:
    body = FIXTURE.read_bytes().replace(b"Page 1 of 9", f"Page {page} of 9".encode())
    previous = _PREVIOUS.replace(b"{}", str(page - 2).encode())
    if last:
        return body.replace(_NEXT, previous)
    return body.replace(
        _NEXT, previous + b"</a> " + _NEXT.replace(b"page=1", f"page={page}".encode())
    )


@pytest.mark.anyio
async def test_split_id_navigates_by_cal_file_and_sub() -> None:
    result, transport = await _page(_as_page(2), "634081", page=2)

    assert result.page is not None
    assert (result.page.page, result.page.previous_page, result.page.next_page) == (2, 1, 3)
    assert transport.requests[0].params == (("file", "634081"), ("page", "1"))


@pytest.mark.anyio
async def test_split_id_past_the_last_page_is_out_of_range() -> None:
    with pytest.raises(CalOutOfRangeError):
        await _page(_as_page(9, last=True), "634081", page=20)


@pytest.mark.anyio
async def test_split_id_rows_must_carry_the_requested_id() -> None:
    body = FIXTURE.read_bytes().replace(b"coord=634081001", b"coord=999999001")

    with pytest.raises(CalParseError):
        await _page(body, "634081")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # links naming two different subs
        (b"&amp;sub=1&amp;cset=R&amp;page=all", b"&amp;sub=2&amp;cset=R&amp;page=all"),
        # a link repeating sub
        (b"&amp;sub=1&amp;cset=R&amp;page=all", b"&amp;sub=1&amp;sub=2&amp;cset=R&amp;page=all"),
    ],
)
async def test_contradictory_cal_links_fail_closed(old: bytes, new: bytes) -> None:
    body = FIXTURE.read_bytes()
    assert old in body

    with pytest.raises(CalParseError):
        await _page(body.replace(old, new), "634081")
