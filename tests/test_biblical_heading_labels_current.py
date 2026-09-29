"""Issue #173: CAL's own book labels in verse headings, and unpadded coordinates.

See docs/research/issue-173-biblical-headings.md (including its 2026-09-29 correction).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.syriac import SyriacParseError, SyriacPeshittaResult, SyriacService
from cal_mcp.targum import TargumParallelResult, TargumParseError, TargumService

FIXTURES = Path(__file__).parent / "fixtures" / "cal"
PESH_PS = FIXTURES / "syriac_peshitta_ps_23_1_current.html"
PESH_KINGS = FIXTURES / "syriac_peshitta_padded_gen_is_1kings_current.html"
PESH_EMPTY_LABEL = FIXTURES / "syriac_peshitta_padded_1sam_empty_label_current.html"
TG_PS = FIXTURES / "targum_parallel_ps_23_1_current.html"


class Recorder:
    def __init__(self, body: bytes, path: str) -> None:
        self.body = body
        self.path = path
        self.requests: list[CalRequest] = []

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        self.requests.append(request)
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/{self.path}",
            body=self.body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )


async def _pesh(
    body: bytes, book: str, chapter: int, verse: int
) -> tuple[SyriacPeshittaResult, Recorder]:
    recorder = Recorder(body, "showpesh.php")
    client = CalHttpClient(transport=recorder)
    try:
        return await SyriacService(client).peshitta_parallel(book, chapter, verse), recorder
    finally:
        await client.aclose()


async def _targum(
    body: bytes, book: str, chapter: int, verse: int
) -> tuple[TargumParallelResult, Recorder]:
    recorder = Recorder(body, "showtargum.php")
    client = CalHttpClient(transport=recorder)
    try:
        return await TargumService(client).parallel(book, chapter, verse), recorder
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_peshitta_request_sends_unpadded_chapter_and_verse() -> None:
    # A zero-padded chapter makes CAL return another verse (research correction).
    result, recorder = await _pesh(PESH_PS.read_bytes(), "Psalms", 23, 1)
    assert result.status.value == "found"
    assert result.book == "Psalms"
    data = dict(recorder.requests[0].data)
    assert (data["chapter"], data["verse"]) == ("23", "1")


@pytest.mark.anyio
async def test_targum_request_sends_unpadded_chapter_and_verse() -> None:
    result, recorder = await _targum(TG_PS.read_bytes(), "Psalms", 23, 1)
    assert result.status.value == "found"
    assert result.readings
    data = dict(recorder.requests[0].data)
    assert (data["chapter"], data["verse"]) == ("23", "1")


@pytest.mark.anyio
async def test_page_for_another_book_than_requested_fails_closed() -> None:
    # CAL answered a padded Genesis request with 1 Kings 1:1 ("Kings1 1:1"); that page
    # must never be returned as Genesis.
    with pytest.raises(SyriacParseError, match="heading"):
        await _pesh(PESH_KINGS.read_bytes(), "Gen", 1, 1)


@pytest.mark.anyio
async def test_cal_heading_label_identifies_its_own_book() -> None:
    result, _ = await _pesh(PESH_KINGS.read_bytes(), "1 Kings", 1, 1)
    assert result.status.value == "found"
    assert result.book == "1 Kings"


@pytest.mark.anyio
async def test_empty_heading_label_fails_closed() -> None:
    with pytest.raises(SyriacParseError, match="heading"):
        await _pesh(PESH_EMPTY_LABEL.read_bytes(), "1 Sam", 1, 1)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("book", "chapter", "verse"),
    [
        ("Job", 23, 1),  # another book's label
        ("Psalms", 23, 2),  # another verse
        ("Psalms", 24, 1),  # another chapter
    ],
)
async def test_heading_for_another_verse_fails_closed(book: str, chapter: int, verse: int) -> None:
    with pytest.raises(SyriacParseError, match="heading"):
        await _pesh(PESH_PS.read_bytes(), book, chapter, verse)


@pytest.mark.anyio
async def test_targum_heading_for_another_book_fails_closed() -> None:
    with pytest.raises(TargumParseError, match="heading"):
        await _targum(TG_PS.read_bytes(), "Proverbs", 23, 1)
