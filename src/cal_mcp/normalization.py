from __future__ import annotations

import string
import unicodedata
from collections.abc import Iterable
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


@dataclass(frozen=True, slots=True)
class NormalizedQuery:
    original: str
    normalized: str
    representation: InputRepresentation
    strategy: NormalizationStrategy


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

_UNICODE_TRANSLITERATION_SPECIAL = frozenset("ˀˁḥṭṗṣšś")
_COMMON_SCRIPT_SEPARATORS = frozenset(" -_'@")
_CAL_CODE_PUNCTUATION = frozenset("()_@%:~+.',;-=$&[]{}<>/#\\^|?*\"")
_CAL_CODE_ALLOWED = frozenset(string.ascii_letters) | _CAL_CODE_PUNCTUATION | {" "}
_CAL_CODE_DISAMBIGUATORS = frozenset("()xTPc$&@_%:~+.',;-=[]{}<>/#\\^|?*\"")


def normalize_query(
    value: str,
    *,
    representation: InputRepresentation | None = None,
) -> NormalizedQuery:
    """Normalize one CAL query without guessing roots, spellings, or morphology."""

    _reject_controls(value)
    candidate = value.strip()
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

    return NormalizedQuery(
        original=value,
        normalized=normalized,
        representation=resolved,
        strategy=strategy,
    )


def encode_pairs(pairs: Iterable[tuple[str, str]]) -> str:
    """Encode ordered/repeated query or form pairs using UTF-8 percent encoding."""

    return urlencode(list(pairs))


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
        if not any(_is_hebrew(char) for char in value) or not all(
            _is_hebrew(char) or char in _COMMON_SCRIPT_SEPARATORS for char in value
        ):
            raise UnsupportedQueryError("query is not valid hebrew-script CAL input")
        return

    if representation is InputRepresentation.SYRIAC:
        if not any(_is_syriac(char) for char in value) or not all(
            _is_syriac(char) or char in _COMMON_SCRIPT_SEPARATORS for char in value
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
        if not all(char in string.ascii_letters or char == " " for char in value):
            raise UnsupportedQueryError("query is not plain shared Roman input")
        return

    raise AssertionError(f"unhandled CAL input representation: {representation}")


def _is_simple_convertible_cal_code(value: str) -> bool:
    return all(char in _CAL_CODE_TO_UNICODE for char in value)


def _is_unicode_transliteration(value: str) -> bool:
    return all(
        char in string.ascii_lowercase
        or char in _UNICODE_TRANSLITERATION_SPECIAL
        or char in _COMMON_SCRIPT_SEPARATORS
        for char in value
    )


def _is_hebrew(char: str) -> bool:
    return "\u0590" <= char <= "\u05ff"


def _is_syriac(char: str) -> bool:
    return "\u0700" <= char <= "\u074f"


__all__ = [
    "AmbiguousQueryError",
    "InputRepresentation",
    "NormalizationError",
    "NormalizationStrategy",
    "NormalizedQuery",
    "UnsupportedQueryError",
    "encode_pairs",
    "normalize_query",
]
