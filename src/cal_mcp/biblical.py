from __future__ import annotations

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


def cal_biblical_book_id(book: str) -> str:
    """Return CAL's current selector ID for one exact biblical book label."""

    if not isinstance(book, str) or book not in _BOOK_IDS:
        raise ValueError("book must be one exact current CAL biblical book label")
    return _BOOK_IDS[book]


__all__ = ["cal_biblical_book_id"]
