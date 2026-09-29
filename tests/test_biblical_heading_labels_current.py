"""Issue #173: CAL's own book labels in Peshitta and Targum verse headings.

See docs/research/issue-173-biblical-headings.md.
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
PESH_GEN = FIXTURES / "syriac_peshitta_gen_1_1_current.html"
TG_PS = FIXTURES / "targum_parallel_ps_23_1_current.html"


def _client(body: bytes, path: str) -> CalHttpClient:
    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config, request
        return CalResponse(
            status_code=200,
            url=f"https://cal.huc.edu/{path}",
            body=body,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 9, 25, tzinfo=UTC),
        )

    return CalHttpClient(transport=transport)


async def _pesh(body: bytes, book: str, chapter: int, verse: int) -> SyriacPeshittaResult:
    client = _client(body, "showpesh.php")
    try:
        return await SyriacService(client).peshitta_parallel(book, chapter, verse)
    finally:
        await client.aclose()


async def _targum(body: bytes, book: str, chapter: int, verse: int) -> TargumParallelResult:
    client = _client(body, "showtargum.php")
    try:
        return await TargumService(client).parallel(book, chapter, verse)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_peshitta_with_cal_abbreviated_book_label_is_read() -> None:
    result = await _pesh(PESH_PS.read_bytes(), "Psalms", 23, 1)
    assert result.status.value == "found"
    assert result.book == "Psalms"
    assert result.peshitta_text is not None


@pytest.mark.anyio
async def test_peshitta_with_cal_wrong_book_label_is_identified_by_navigation() -> None:
    # CAL heads Genesis 1:1 "Kings1 1:1"; its navigation still names book 1 (#173).
    result = await _pesh(PESH_GEN.read_bytes(), "Gen", 1, 1)
    assert result.status.value == "found"
    assert result.book == "Gen"


@pytest.mark.anyio
async def test_targum_with_cal_abbreviated_book_label_is_read() -> None:
    result = await _targum(TG_PS.read_bytes(), "Psalms", 23, 1)
    assert result.status.value == "found"
    assert result.book == "Psalms"
    assert result.readings


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old", "new"),
    [
        # Navigation naming another book.
        ("bookname=27&chapter=023&verse=2", "bookname=28&chapter=023&verse=2"),
        # Navigation naming another chapter.
        ("bookname=27&chapter=023&verse=2", "bookname=27&chapter=024&verse=2"),
        # Navigation more than one verse away.
        ("bookname=27&chapter=023&verse=2", "bookname=27&chapter=023&verse=9"),
        # Heading for another verse.
        ("for Ps 23:1", "for Ps 23:2"),
        # Heading for another chapter.
        ("for Ps 23:1", "for Ps 24:1"),
    ],
)
async def test_peshitta_identity_mismatch_fails_closed(old: str, new: str) -> None:
    body = PESH_PS.read_text(encoding="utf-8")
    assert old in body
    with pytest.raises(SyriacParseError):
        await _pesh(body.replace(old, new, 1).encode(), "Psalms", 23, 1)


@pytest.mark.anyio
async def test_abbreviated_label_without_navigation_fails_closed() -> None:
    body = PESH_PS.read_text(encoding="utf-8")
    for old in (
        "showpesh.php?bookname=27&chapter=023&verse=0",
        "showpesh.php?bookname=27&chapter=023&verse=2",
    ):
        assert old in body
        body = body.replace(old, "showpesh.php", 1)
    with pytest.raises(SyriacParseError):
        await _pesh(body.encode(), "Psalms", 23, 1)


@pytest.mark.anyio
async def test_targum_navigation_naming_another_book_fails_closed() -> None:
    body = TG_PS.read_text(encoding="utf-8").replace(
        "bookname=27&chapter=023&verse=0&", "bookname=26&chapter=023&verse=0&", 1
    )
    with pytest.raises(TargumParseError):
        await _targum(body.encode(), "Psalms", 23, 1)
