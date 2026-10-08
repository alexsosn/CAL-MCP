from __future__ import annotations

import pytest

from cal_mcp.normalization import UnsupportedQueryError, convert_to_cal_code

_SHIN_SIN_MESSAGE = "Hebrew shin/sin conversion supports only one explicit shin or sin dot"


def _message(value: str) -> str:
    with pytest.raises(UnsupportedQueryError) as exc_info:
        convert_to_cal_code(value)
    return str(exc_info.value)


def test_pointed_shin_word_reports_the_vowel_not_the_shin_dot() -> None:
    message = _message("שָׁלוֹם")

    assert _SHIN_SIN_MESSAGE not in message
    assert "U+05B8 HEBREW POINT QAMATS" in message
    assert "שׁלום" in message


def test_vowel_on_another_letter_names_the_mark_and_suggests_unpointed_form() -> None:
    # Canonical order puts qamats (ccc 18) before dagesh (ccc 21); the first mark is named.
    message = _message("בָּרָא")

    assert "U+05B8 HEBREW POINT QAMATS" in message
    assert "ברא" in message


def test_dagesh_with_shin_dot_reports_the_dagesh() -> None:
    message = _message("שּׁ")

    assert _SHIN_SIN_MESSAGE not in message
    assert "U+05BC HEBREW POINT DAGESH OR MAPIQ" in message


@pytest.mark.parametrize("value", ["שׁׁ", "שׁׂ"])
def test_multiple_shin_sin_dots_keep_the_shin_sin_message(value: str) -> None:
    assert _SHIN_SIN_MESSAGE in _message(value)


def test_unmapped_hebrew_punctuation_is_named() -> None:
    assert "U+05BE HEBREW PUNCTUATION MAQAF" in _message("מלך־רב")


def test_unanchored_leading_mark_is_named() -> None:
    assert "U+05B8 HEBREW POINT QAMATS" in _message("ָמלך")
