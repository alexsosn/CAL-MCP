"""Issue #186: six-digit Syriac text ids are CAL file plus subtext (634081 = 63408 + 1).

See docs/research/issue-186-six-digit-syriac-id.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalParseError
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


async def _page(body: bytes, file_id: str) -> tuple[TextPageResult, FixtureTransport]:
    transport = FixtureTransport(body)
    client = CalHttpClient(transport=transport)
    try:
        return await TextService(client).page(file_id), transport
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
    assert [line.coordinate for line in result.page.lines][:1] == ["634081001"]
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
