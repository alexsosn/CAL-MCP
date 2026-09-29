from __future__ import annotations

import re

from cal_mcp.errors import CalInputError

_BOOK_IDS = {
    "Gen": "01",
    "Exod": "02",
    "Levit": "03",
    "Numb": "04",
    "Deut": "05",
    "Joshua": "06",
    "Judges": "07",
    "1 Sam": "08",
    "2 Sam": "09",
    "1 Kings": "10",
    "2 Kings": "11",
    "Isaiah": "12",
    "Jeremiah": "13",
    "Ezekiel": "14",
    "Hosea": "15",
    "Joel": "16",
    "Amos": "17",
    "Obadiah": "18",
    "Jonah": "19",
    "Micah": "20",
    "Nahum": "21",
    "Hab.": "22",
    "Zeph.": "23",
    "Haggai": "24",
    "Zechariah": "25",
    "Malachi": "26",
    "Psalms": "27",
    "Job": "28",
    "Song of Songs": "29",
    "Ruth": "30",
    "Qoheleth": "31",
    "Lamentations": "32",
    "Proverbs": "33",
    "1 Chronicles": "34",
    "2 Chronicles": "35",
    "Esther": "36",
}


# CAL's own book label in its MT/Peshitta and MT/Targum verse headings, recorded for all
# 36 books on 2026-09-29 (R-044). It identifies the verse CAL actually returned.
_CAL_HEADING_LABELS = {
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
_HEADING_VERSE_RE = re.compile(r"(?P<label>\S+) (?P<chapter>\d+):(?P<verse>\d+)")


def cal_biblical_book_id(book: str) -> str:
    """Return CAL's current selector ID for one exact biblical book label."""

    if not isinstance(book, str) or book not in _BOOK_IDS:
        raise CalInputError("book must be one exact current CAL biblical book label")
    return _BOOK_IDS[book]


def cal_biblical_heading_matches(heading: str, *, book: str, chapter: int, verse: int) -> bool:
    """Whether a verse heading (after its prefix) names the requested book, chapter and verse.

    The book may appear as CAL's heading label for that book or as the exact selector
    label (the earlier layout). A page for any other book, or with an empty label, does
    not match, so a shifted CAL coordinate can never be served as the requested verse.
    """

    found = _HEADING_VERSE_RE.fullmatch(heading)
    if found is None:
        return False
    return (
        found.group("label") in {book, _CAL_HEADING_LABELS.get(book)}
        and int(found.group("chapter")) == chapter
        and int(found.group("verse")) == verse
    )


__all__ = ["cal_biblical_book_id", "cal_biblical_heading_matches"]
