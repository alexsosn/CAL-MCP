"""Issue #173: CAL's own book labels in Peshitta and Targum verse headings.

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
PESH_1KINGS = FIXTURES / "syriac_peshitta_1kings_1_1_current.html"
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
async def test_peshitta_request_keeps_cal_two_digit_coordinates() -> None:
    # CAL's own links use two-digit chapters/verses; a three-digit chapter makes CAL
    # return another verse (research correction), so the format must not change.
    result, recorder = await _pesh(PESH_PS.read_bytes(), "Psalms", 23, 1)
    assert result.status.value == "found"
    assert result.book == "Psalms"
    data = dict(recorder.requests[0].data)
    assert (data["chapter"], data["verse"]) == ("23", "01")


@pytest.mark.anyio
async def test_targum_request_keeps_cal_two_digit_coordinates() -> None:
    result, recorder = await _targum(TG_PS.read_bytes(), "Psalms", 23, 1)
    assert result.status.value == "found"
    assert result.readings
    data = dict(recorder.requests[0].data)
    assert (data["chapter"], data["verse"]) == ("23", "01")


@pytest.mark.anyio
async def test_page_for_another_book_than_requested_fails_closed() -> None:
    # CAL answers a three-digit-chapter Genesis request with 1 Kings 1:1 ("Kings1 1:1");
    # a page for another book must never be returned as the requested one.
    with pytest.raises(SyriacParseError, match="heading"):
        await _pesh(PESH_KINGS.read_bytes(), "Gen", 1, 1)


@pytest.mark.anyio
async def test_cal_heading_label_identifies_its_own_book() -> None:
    result, _ = await _pesh(PESH_1KINGS.read_bytes(), "1 Kings", 1, 1)
    assert result.status.value == "found"
    assert result.book == "1 Kings"


@pytest.mark.anyio
async def test_empty_heading_label_fails_closed() -> None:
    # CAL's " 1:1" collapses to "1:1", which has no book label at all, so the heading
    # shape itself fails; the label table is not reached.
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


# CAL's current heading labels, captured for all 36 selector books (R-044).
_EXPECTED_HEADING_LABELS = {
    "Gen": "Gen",
    "Exod": "Exod",
    "Levit": "Lev",
    "Numb": "Num",
    "Deut": "Deut",
    "Joshua": "Joshua",
    "Judges": "Judges",
    "1 Sam": "Sam1",
    "2 Sam": "Sam2",
    "1 Kings": "Kings1",
    "2 Kings": "Kings2",
    "Isaiah": "Isaiah",
    "Jeremiah": "Jer",
    "Ezekiel": "Ezek",
    "Hosea": "Hosea",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obadiah": "Obad",
    "Jonah": "Jonah",
    "Micah": "Micah",
    "Nahum": "Nahum",
    "Hab.": "Hab",
    "Zeph.": "Zeph",
    "Haggai": "Haggai",
    "Zechariah": "Zech",
    "Malachi": "Mal",
    "Psalms": "Ps",
    "Job": "Job",
    "Song of Songs": "Song",
    "Ruth": "Ruth",
    "Qoheleth": "Qoheleth",
    "Lamentations": "Lam",
    "Proverbs": "Prov",
    "1 Chronicles": "Chron1",
    "2 Chronicles": "Chron2",
    "Esther": "Esther",
}


def test_heading_label_table_covers_every_selector_book_with_distinct_labels() -> None:
    from cal_mcp.biblical import _BOOK_IDS, _CAL_HEADING_LABELS

    assert dict(_CAL_HEADING_LABELS) == _EXPECTED_HEADING_LABELS
    assert set(_CAL_HEADING_LABELS) == set(_BOOK_IDS)
    assert len(set(_CAL_HEADING_LABELS.values())) == len(_CAL_HEADING_LABELS)


@pytest.mark.parametrize(("book", "label"), sorted(_EXPECTED_HEADING_LABELS.items()))
def test_each_cal_heading_label_matches_only_its_book(book: str, label: str) -> None:
    from cal_mcp.biblical import cal_biblical_heading_matches

    assert cal_biblical_heading_matches(f"{label} 3:4", book=book, chapter=3, verse=4)
    others = [other for other in _EXPECTED_HEADING_LABELS if other != book]
    assert not any(
        cal_biblical_heading_matches(f"{label} 3:4", book=other, chapter=3, verse=4)
        for other in others
    )


@pytest.mark.parametrize("book", ["1 Sam", "Song of Songs", "2 Chronicles", "Hab."])
def test_exact_selector_label_heading_still_matches(book: str) -> None:
    from cal_mcp.biblical import cal_biblical_heading_matches

    assert cal_biblical_heading_matches(f"{book} 1:1", book=book, chapter=1, verse=1)


@pytest.mark.parametrize("heading", ["Ps ２3:1", "Ps 23:１", "Ps 23:1 ", " Ps 23:1", "Ps 23:1:1"])
def test_heading_numbers_must_be_exact_ascii(heading: str) -> None:
    from cal_mcp.biblical import cal_biblical_heading_matches

    assert not cal_biblical_heading_matches(heading, book="Psalms", chapter=23, verse=1)
