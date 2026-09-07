from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlencode


class NormalizationError(ValueError):
    """Base class for deterministic CAL input normalization failures."""


class AmbiguousQueryError(NormalizationError):
    """Raised when input mixes representations that cannot be chosen safely."""


class UnsupportedQueryError(NormalizationError):
    """Raised when input is outside the locally documented CAL query contract."""


class InputRepresentation(StrEnum):
    """Representations accepted by CAL or detected without linguistic inference."""

    CAL_CODE = "cal_code"
    UNICODE_TRANSLITERATION = "unicode_transliteration"
    HEBREW = "hebrew"
    SYRIAC = "syriac"
    ROMAN_SHARED = "roman_shared"


class NormalizationStrategy(StrEnum):
    """Deterministic transformation applied before endpoint-specific encoding."""

    PASS_THROUGH = "pass_through"
    CAL_CODE_TO_UNICODE = "cal_code_to_unicode"


class CalCodeConversionStrategy(StrEnum):
    """Deterministic transformation used to produce CAL Roman code."""

    PASS_THROUGH = "pass_through"
    UNICODE_TRANSLITERATION_TO_CAL_CODE = "unicode_transliteration_to_cal_code"
    HEBREW_TO_CAL_CODE = "hebrew_to_cal_code"
    SYRIAC_TO_CAL_CODE = "syriac_to_cal_code"


@dataclass(frozen=True, slots=True)
class NormalizedQuery:
    original: str
    normalized: str
    representation: InputRepresentation
    strategy: NormalizationStrategy


@dataclass(frozen=True, slots=True)
class CalCodeConversion:
    original: str
    cal_code: str
    representation: InputRepresentation
    strategy: CalCodeConversionStrategy

    def to_dict(self) -> dict[str, object]:
        return {
            "original": self.original,
            "cal_code": self.cal_code,
            "representation": self.representation.value,
            "strategy": self.strategy.value,
        }


# Current CAL lexicon browser table, searching/fullbrowser.html (rechecked 2026-09-04).
# Only this simple consonantal subset is converted locally. CAL code containing other
# documented punctuation/diacritic syntax is sent through unchanged instead of being
# combined with a partial Unicode conversion.
_CAL_CODE_TO_UNICODE = {
    ")": "ˀ",
    "b": "b",
    "g": "g",
    "d": "d",
    "h": "h",
    "w": "w",
    "z": "z",
    "x": "ḥ",
    "T": "ṭ",
    "y": "y",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "s": "s",
    "(": "ˁ",
    "p": "p",
    "P": "ṗ",
    "c": "ṣ",
    "q": "q",
    "r": "r",
    "$": "š",
    "&": "ś",
    "t": "t",
    "@": " ",
    "_": "_",
    " ": " ",
}

_UNICODE_TRANSLITERATION_TO_CAL_CODE = {
    "ˀ": ")",
    "ˁ": "(",
    "ḥ": "x",
    "ṭ": "T",
    "ṗ": "P",
    "ṣ": "c",
    "š": "$",
    "ś": "&",
}

_HEBREW_TO_CAL_CODE = {
    "א": ")",
    "ב": "b",
    "ג": "g",
    "ד": "d",
    "ה": "h",
    "ו": "w",
    "ז": "z",
    "ח": "x",
    "ט": "T",
    "י": "y",
    "כ": "k",
    "ך": "k",
    "ל": "l",
    "מ": "m",
    "ם": "m",
    "נ": "n",
    "ן": "n",
    "ס": "s",
    "ע": "(",
    "פ": "p",
    "ף": "p",
    "צ": "c",
    "ץ": "c",
    "ק": "q",
    "ר": "r",
    "ת": "t",
}
_HEBREW_SHIN = "ש"
_HEBREW_SHIN_DOT = "\u05c1"
_HEBREW_SIN_DOT = "\u05c2"

_SYRIAC_TO_CAL_CODE = {
    "ܐ": ")",
    "ܒ": "b",
    "ܓ": "g",
    "ܕ": "d",
    "ܗ": "h",
    "ܘ": "w",
    "ܙ": "z",
    "ܚ": "x",
    "ܛ": "T",
    "ܝ": "y",
    "ܟ": "k",
    "ܠ": "l",
    "ܡ": "m",
    "ܢ": "n",
    "ܣ": "s",
    "ܥ": "(",
    "ܦ": "p",
    "ܨ": "c",
    "ܩ": "q",
    "ܪ": "r",
    "ܫ": "$",
    "ܬ": "t",
}

# Roman consonants whose CAL-code and current documented Unicode spellings are identical.
# Plain input using only these characters is genuinely shared and must not be guessed.
_SHARED_ROMAN_LETTERS = frozenset("bgdhwzyklmnspqrt")
_UNICODE_TRANSLITERATION_SPECIAL = frozenset("ˀˁḥṭṗṣšś")
_UNICODE_SEPARATORS = frozenset(" _")
_SCRIPT_SEPARATORS = frozenset(" _")

# CAL's broader Roman coding conventions (prova.html, rechecked 2026-09-04) add Jewish
# Aramaic vowels, Syriac diacritic codes, Mandaic letters, and manuscript/editorial syntax.
# Keep this whitelist explicit so arbitrary ASCII is never mislabeled as documented CAL code.
_CAL_CODE_LETTERS = frozenset(")bgdhwzxTyklmns(pPcqr$&taAeEiuUoOFDHS")
_CAL_CODE_SYNTAX = frozenset(":._~+',;%@\"-={}<>/#\\[]^|?*")
_CAL_CODE_ALLOWED = _CAL_CODE_LETTERS | _CAL_CODE_SYNTAX | {" "}
_CAL_CODE_DISAMBIGUATORS = _CAL_CODE_ALLOWED - _SHARED_ROMAN_LETTERS - {" "}


def normalize_query(
    value: str,
    *,
    representation: InputRepresentation | None = None,
) -> NormalizedQuery:
    """Normalize one CAL query without guessing roots, spellings, or morphology."""

    _reject_controls(value)
    # Only the ordinary ASCII space is a documented query separator. Do not let
    # str.strip() silently erase NBSP or other Unicode whitespace before validation.
    candidate = value.strip(" ")
    if not candidate:
        raise UnsupportedQueryError("CAL query is empty after trimming surrounding spaces")

    resolved = representation or _detect_representation(candidate)
    _validate_representation(candidate, resolved)

    if resolved is InputRepresentation.CAL_CODE and _is_simple_convertible_cal_code(candidate):
        normalized = "".join(_CAL_CODE_TO_UNICODE[char] for char in candidate)
        strategy = NormalizationStrategy.CAL_CODE_TO_UNICODE
    else:
        normalized = candidate
        strategy = NormalizationStrategy.PASS_THROUGH

    if not normalized.strip(" "):
        raise UnsupportedQueryError("CAL query is empty after normalization")

    return NormalizedQuery(
        original=value,
        normalized=normalized,
        representation=resolved,
        strategy=strategy,
    )


def convert_to_cal_code(
    value: str,
    *,
    representation: InputRepresentation | None = None,
) -> CalCodeConversion:
    """Convert one supported representation to CAL Roman code without linguistic guessing."""

    _reject_controls(value)
    candidate = value.strip(" ")
    if not candidate:
        raise UnsupportedQueryError("CAL input is empty after trimming surrounding spaces")

    resolved = representation or _detect_representation(candidate)
    _validate_representation(candidate, resolved)

    if resolved in {InputRepresentation.CAL_CODE, InputRepresentation.ROMAN_SHARED}:
        cal_code = candidate
        strategy = CalCodeConversionStrategy.PASS_THROUGH
    elif resolved is InputRepresentation.UNICODE_TRANSLITERATION:
        cal_code = _convert_unicode_transliteration_to_cal_code(candidate)
        strategy = CalCodeConversionStrategy.UNICODE_TRANSLITERATION_TO_CAL_CODE
    elif resolved is InputRepresentation.HEBREW:
        cal_code = _convert_hebrew_to_cal_code(candidate)
        strategy = CalCodeConversionStrategy.HEBREW_TO_CAL_CODE
    elif resolved is InputRepresentation.SYRIAC:
        cal_code = _convert_syriac_to_cal_code(candidate)
        strategy = CalCodeConversionStrategy.SYRIAC_TO_CAL_CODE
    else:
        raise AssertionError(f"unhandled CAL input representation: {resolved}")

    if not cal_code.strip(" "):
        raise UnsupportedQueryError("CAL input is empty after conversion")

    return CalCodeConversion(
        original=value,
        cal_code=cal_code,
        representation=resolved,
        strategy=strategy,
    )


def encode_pairs(pairs: Iterable[tuple[str, str]]) -> str:
    """Encode ordered/repeated query or form pairs using UTF-8 percent encoding."""

    return urlencode(list(pairs))


def _convert_unicode_transliteration_to_cal_code(value: str) -> str:
    converted: list[str] = []
    for char in value:
        if char in _SHARED_ROMAN_LETTERS or char == " ":
            converted.append(char)
            continue
        mapped = _UNICODE_TRANSLITERATION_TO_CAL_CODE.get(char)
        if mapped is None:
            raise UnsupportedQueryError(
                "unicode_transliteration contains a character without a v0.1 CAL-code mapping"
            )
        converted.append(mapped)
    return "".join(converted)


def _convert_hebrew_to_cal_code(value: str) -> str:
    converted: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == " ":
            converted.append(char)
            index += 1
            continue

        if char == _HEBREW_SHIN:
            following_marks: list[str] = []
            mark_index = index + 1
            while mark_index < len(value) and unicodedata.category(value[mark_index]).startswith("M"):
                following_marks.append(value[mark_index])
                mark_index += 1
            if following_marks == [_HEBREW_SHIN_DOT]:
                converted.append("$")
                index = mark_index
                continue
            if following_marks == [_HEBREW_SIN_DOT]:
                converted.append("&")
                index = mark_index
                continue
            if not following_marks:
                raise AmbiguousQueryError("bare Hebrew ש is ambiguous between CAL shin and sin")
            raise UnsupportedQueryError(
                "Hebrew shin/sin conversion supports only one explicit shin or sin dot"
            )

        mapped = _HEBREW_TO_CAL_CODE.get(char)
        if mapped is None:
            raise UnsupportedQueryError(
                "Hebrew input contains a mark, punctuation sign, or letter without a v0.1 "
                "CAL-code mapping"
            )
        converted.append(mapped)
        index += 1

        if index < len(value) and unicodedata.category(value[index]).startswith("M"):
            raise UnsupportedQueryError(
                "Hebrew vowel, accent, or combining marks are not converted to CAL code in v0.1"
            )

    return "".join(converted)


def _convert_syriac_to_cal_code(value: str) -> str:
    converted: list[str] = []
    for char in value:
        if char == " ":
            converted.append(char)
            continue
        mapped = _SYRIAC_TO_CAL_CODE.get(char)
        if mapped is None:
            raise UnsupportedQueryError(
                "Syriac input contains a mark, punctuation sign, or letter without a v0.1 "
                "CAL-code mapping"
            )
        converted.append(mapped)
    return "".join(converted)


def _reject_controls(value: str) -> None:
    if any(unicodedata.category(char) in {"Cc", "Cs"} for char in value):
        raise UnsupportedQueryError("CAL query contains control or surrogate characters")


def _detect_representation(value: str) -> InputRepresentation:
    has_hebrew = any(_is_hebrew(char) for char in value)
    has_syriac = any(_is_syriac(char) for char in value)

    if has_hebrew and has_syriac:
        raise AmbiguousQueryError("mixed Hebrew and Syriac query input is ambiguous")
    if has_hebrew:
        return InputRepresentation.HEBREW
    if has_syriac:
        return InputRepresentation.SYRIAC

    if any(ord(char) > 127 for char in value):
        if _is_unicode_transliteration(value):
            return InputRepresentation.UNICODE_TRANSLITERATION
        raise UnsupportedQueryError("query contains unsupported Unicode transliteration characters")

    if not all(char in _CAL_CODE_ALLOWED for char in value):
        raise UnsupportedQueryError("query contains unsupported CAL/Roman characters")

    if any(char in _CAL_CODE_DISAMBIGUATORS for char in value):
        return InputRepresentation.CAL_CODE
    return InputRepresentation.ROMAN_SHARED


def _validate_representation(value: str, representation: InputRepresentation) -> None:
    if representation is InputRepresentation.HEBREW:
        if not _contains_script_letter(value, _is_hebrew) or not all(
            _is_hebrew(char) or char in _SCRIPT_SEPARATORS for char in value
        ):
            raise UnsupportedQueryError("query is not valid hebrew-script CAL input")
        return

    if representation is InputRepresentation.SYRIAC:
        if not _contains_script_letter(value, _is_syriac) or not all(
            _is_syriac(char) or char in _SCRIPT_SEPARATORS for char in value
        ):
            raise UnsupportedQueryError("query is not valid syriac-script CAL input")
        return

    if representation is InputRepresentation.UNICODE_TRANSLITERATION:
        if not _is_unicode_transliteration(value):
            raise UnsupportedQueryError("query is not documented unicode_transliteration input")
        return

    if representation is InputRepresentation.CAL_CODE:
        if not all(char in _CAL_CODE_ALLOWED for char in value):
            raise UnsupportedQueryError("query is not valid cal_code input")
        return

    if representation is InputRepresentation.ROMAN_SHARED:
        if not all(char in _SHARED_ROMAN_LETTERS or char == " " for char in value):
            raise UnsupportedQueryError("query is not plain shared Roman input")
        return

    raise AssertionError(f"unhandled CAL input representation: {representation}")


def _is_simple_convertible_cal_code(value: str) -> bool:
    return all(char in _CAL_CODE_TO_UNICODE for char in value)


def _is_unicode_transliteration(value: str) -> bool:
    return all(
        char in _SHARED_ROMAN_LETTERS
        or char in _UNICODE_TRANSLITERATION_SPECIAL
        or char in _UNICODE_SEPARATORS
        for char in value
    )


def _contains_script_letter(value: str, in_script: Callable[[str], bool]) -> bool:
    return any(in_script(char) and unicodedata.category(char).startswith("L") for char in value)


def _is_hebrew(char: str) -> bool:
    return "\u0590" <= char <= "\u05ff"


def _is_syriac(char: str) -> bool:
    return "\u0700" <= char <= "\u074f"


__all__ = [
    "AmbiguousQueryError",
    "CalCodeConversion",
    "CalCodeConversionStrategy",
    "InputRepresentation",
    "NormalizationError",
    "NormalizationStrategy",
    "NormalizedQuery",
    "UnsupportedQueryError",
    "convert_to_cal_code",
    "encode_pairs",
    "normalize_query",
]
