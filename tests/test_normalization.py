from __future__ import annotations

import pytest

from cal_mcp.normalization import (
    AmbiguousQueryError,
    InputRepresentation,
    NormalizationStrategy,
    UnsupportedQueryError,
    encode_pairs,
    normalize_query,
)


@pytest.mark.parametrize(
    ("value", "representation"),
    [
        ("šˀwl", InputRepresentation.UNICODE_TRANSLITERATION),
        ("מלכ", InputRepresentation.HEBREW),
        ("ܡܠܟ", InputRepresentation.SYRIAC),
    ],
)
def test_cal_supported_unicode_representations_pass_through(
    value: str,
    representation: InputRepresentation,
) -> None:
    result = normalize_query(value)

    assert result.original == value
    assert result.normalized == value
    assert result.representation is representation
    assert result.strategy is NormalizationStrategy.PASS_THROUGH


def test_plain_roman_shared_input_is_preserved_without_guessing_between_equivalent_encodings() -> None:
    result = normalize_query("  mlk  ")

    assert result.original == "  mlk  "
    assert result.normalized == "mlk"
    assert result.representation is InputRepresentation.ROMAN_SHARED
    assert result.strategy is NormalizationStrategy.PASS_THROUGH


def test_internal_spaces_are_semantic_and_are_not_collapsed() -> None:
    result = normalize_query("  br  mwtˀ  ")

    assert result.original == "  br  mwtˀ  "
    assert result.normalized == "br  mwtˀ"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("$)wl", "šˀwl"),
        ("br@mwt)", "br mwtˀ"),
        ("w_", "w_"),
    ],
)
def test_simple_cal_code_uses_documented_table_driven_unicode_conversion(
    value: str,
    expected: str,
) -> None:
    result = normalize_query(value, representation=InputRepresentation.CAL_CODE)

    assert result.original == value
    assert result.normalized == expected
    assert result.representation is InputRepresentation.CAL_CODE
    assert result.strategy is NormalizationStrategy.CAL_CODE_TO_UNICODE


def test_cal_code_with_documented_non_consonantal_punctuation_is_passed_through() -> None:
    result = normalize_query("mlk%", representation=InputRepresentation.CAL_CODE)

    assert result.normalized == "mlk%"
    assert result.representation is InputRepresentation.CAL_CODE
    assert result.strategy is NormalizationStrategy.PASS_THROUGH


def test_explicit_override_disambiguates_plain_roman_input() -> None:
    cal_code = normalize_query("mlk", representation=InputRepresentation.CAL_CODE)
    unicode_value = normalize_query(
        "mlk",
        representation=InputRepresentation.UNICODE_TRANSLITERATION,
    )

    assert cal_code.representation is InputRepresentation.CAL_CODE
    assert cal_code.strategy is NormalizationStrategy.CAL_CODE_TO_UNICODE
    assert unicode_value.representation is InputRepresentation.UNICODE_TRANSLITERATION
    assert unicode_value.strategy is NormalizationStrategy.PASS_THROUGH


def test_incompatible_explicit_override_is_rejected() -> None:
    with pytest.raises(UnsupportedQueryError, match="hebrew"):
        normalize_query("mlk", representation=InputRepresentation.HEBREW)


def test_mixed_hebrew_and_syriac_is_explicitly_ambiguous() -> None:
    with pytest.raises(AmbiguousQueryError, match="mixed"):
        normalize_query("מלܟ")


@pytest.mark.parametrize(
    "value",
    [
        "mlk🙂",
        "mālk",
        "mlk\n",
    ],
)
def test_unsupported_or_control_characters_are_rejected(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        normalize_query(value)


def test_empty_after_trimming_is_rejected_without_losing_original_input() -> None:
    with pytest.raises(UnsupportedQueryError, match="empty"):
        normalize_query("   ")


def test_query_and_form_pair_encoding_is_ordered_repeated_and_utf8_safe() -> None:
    encoded = encode_pairs(
        (
            ("lemma", "br mwtˀ"),
            ("q", "a+b%&"),
            ("q", "ܡܠܟ"),
        )
    )

    assert encoded == "lemma=br+mwt%CB%80&q=a%2Bb%25%26&q=%DC%A1%DC%A0%DC%9F"
