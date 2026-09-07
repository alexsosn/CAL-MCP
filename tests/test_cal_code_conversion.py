from __future__ import annotations

import importlib
import socket
import sys

import pytest
from mcp import Client

from cal_mcp.normalization import (
    CalCodeConversionStrategy,
    InputRepresentation,
    UnsupportedQueryError,
    convert_to_cal_code,
    normalize_query,
)


def test_unicode_transliteration_maps_to_exact_cal_code() -> None:
    result = convert_to_cal_code("  šˀl ḥṭˁ ṗṣś  ")

    assert result.original == "  šˀl ḥṭˁ ṗṣś  "
    assert result.words[0].candidates == ("$)l",)
    assert result.words[1].candidates == ("xT(",)
    assert result.words[2].candidates == ("Pc&",)
    assert result.representation is InputRepresentation.UNICODE_TRANSLITERATION
    assert result.strategy is CalCodeConversionStrategy.UNICODE_TRANSLITERATION_TO_CAL_CODE


def test_shared_roman_consonants_are_single_candidates() -> None:
    result = convert_to_cal_code("  mlk  br  ")

    assert [word.original for word in result.words] == ["mlk", "br"]
    assert [word.candidates for word in result.words] == [("mlk",), ("br",)]
    assert result.representation is InputRepresentation.ROMAN_SHARED
    assert result.strategy is CalCodeConversionStrategy.PASS_THROUGH


def test_hebrew_medial_and_final_consonants_map_to_one_candidate() -> None:
    result = convert_to_cal_code("אבגדהוזחטיכךלמםנןסעפףצץקרת")

    assert result.words[0].candidates == (")bgdhwzxTykklmmnns(ppccqrt",)
    assert result.representation is InputRepresentation.HEBREW
    assert result.strategy is CalCodeConversionStrategy.HEBREW_TO_CAL_CODE


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("שׁלם", "$lm"),
        ("שׂלם", "&lm"),
    ],
)
def test_hebrew_shin_and_sin_are_deterministic_with_explicit_dot(
    value: str,
    expected: str,
) -> None:
    result = convert_to_cal_code(value)
    assert result.words[0].candidates == (expected,)
    assert result.words[0].ambiguities == ()


def test_bare_hebrew_shin_returns_both_cal_candidates() -> None:
    result = convert_to_cal_code("שלם")

    assert result.words[0].candidates == ("$lm", "&lm")
    assert len(result.words[0].ambiguities) == 1
    ambiguity = result.words[0].ambiguities[0]
    assert ambiguity.input == "ש"
    assert ambiguity.cal_codes == ("$", "&")


def test_multiple_ambiguous_graphemes_expand_in_stable_order() -> None:
    result = convert_to_cal_code("שש")

    assert result.words[0].candidates == ("$$", "$&", "&$", "&&")


def test_ambiguity_is_tracked_per_word() -> None:
    result = convert_to_cal_code("שלם בר שש")

    assert [word.candidates for word in result.words] == [
        ("$lm", "&lm"),
        ("br",),
        ("$$", "$&", "&$", "&&"),
    ]


@pytest.mark.parametrize(
    "value",
    [
        "מֶלֶךְ",
        "בּר",
        "מ֣לך",
        "מלך־רב",
    ],
)
def test_hebrew_marks_are_not_silently_stripped(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


def test_candidate_expansion_over_limit_fails_instead_of_truncating() -> None:
    with pytest.raises(Exception) as exc_info:
        convert_to_cal_code("שששששש")

    assert exc_info.type.__name__ == "ConversionExpansionError"
    assert any(token in str(exc_info.value) for token in ("32", "candidate", "expansion"))


def test_syriac_consonants_map_to_cal_code() -> None:
    result = convert_to_cal_code("ܐܒܓܕܗܘܙܚܛܝܟܠܡܢܣܥܦܨܩܪܫܬ")

    assert result.words[0].candidates == (")bgdhwzxTyklmns(pcqr$t",)
    assert result.representation is InputRepresentation.SYRIAC
    assert result.strategy is CalCodeConversionStrategy.SYRIAC_TO_CAL_CODE


@pytest.mark.parametrize(
    "value",
    [
        "ܡܲܠܟܵܐ",
        "ܡ݁ܠܟ",
        "ܡܠܟ܂",
    ],
)
def test_syriac_marks_and_punctuation_are_not_silently_stripped(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


def test_valid_explicit_cal_code_passes_through_as_one_candidate() -> None:
    result = convert_to_cal_code(
        "mlk%",
        representation=InputRepresentation.CAL_CODE,
    )

    assert result.words[0].candidates == ("mlk%",)
    assert result.representation is InputRepresentation.CAL_CODE
    assert result.strategy is CalCodeConversionStrategy.PASS_THROUGH


def test_simple_cal_code_round_trips_through_existing_unicode_normalization() -> None:
    cal_code = ")bgdhwzxTyklmns(pPcqr$&t"
    unicode_value = normalize_query(
        cal_code,
        representation=InputRepresentation.CAL_CODE,
    ).normalized

    result = convert_to_cal_code(
        unicode_value,
        representation=InputRepresentation.UNICODE_TRANSLITERATION,
    )

    assert result.words[0].candidates == (cal_code,)


@pytest.mark.parametrize("value", ["מלܟ", "mlk🙂", "mlk\n"])
def test_unsupported_or_control_input_fails_closed(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


@pytest.mark.anyio
async def test_public_conversion_tool_exposes_candidates_and_is_local_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("cal_convert_to_code must be local-only")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        tool = tools["cal_convert_to_code"]
        assert set(tool.input_schema["properties"]) == {"value", "representation"}
        assert tool.input_schema["required"] == ["value"]

        response = await client.call_tool("cal_convert_to_code", {"value": "שלם"})

    assert response.structured_content == {
        "original": "שלם",
        "representation": "hebrew",
        "strategy": "hebrew_to_cal_code",
        "words": [
            {
                "original": "שלם",
                "candidates": ["$lm", "&lm"],
                "ambiguities": [
                    {
                        "index": 0,
                        "input": "ש",
                        "cal_codes": ["$", "&"],
                    }
                ],
            }
        ],
    }
