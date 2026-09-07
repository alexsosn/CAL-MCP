from __future__ import annotations

import importlib
import socket
import sys

import pytest
from mcp import Client

from cal_mcp.normalization import (
    AmbiguousQueryError,
    CalCodeConversionStrategy,
    InputRepresentation,
    UnsupportedQueryError,
    convert_to_cal_code,
    normalize_query,
)


def test_unicode_transliteration_maps_to_exact_cal_code() -> None:
    result = convert_to_cal_code("  šˀl ḥṭˁ ṗṣś  ")

    assert result.original == "  šˀl ḥṭˁ ṗṣś  "
    assert result.cal_code == "$)l xT( Pc&"
    assert result.representation is InputRepresentation.UNICODE_TRANSLITERATION
    assert result.strategy is CalCodeConversionStrategy.UNICODE_TRANSLITERATION_TO_CAL_CODE


def test_shared_roman_consonants_are_already_valid_cal_code() -> None:
    result = convert_to_cal_code("  mlk  br  ")

    assert result.cal_code == "mlk  br"
    assert result.representation is InputRepresentation.ROMAN_SHARED
    assert result.strategy is CalCodeConversionStrategy.PASS_THROUGH


def test_hebrew_medial_and_final_consonants_map_to_cal_code() -> None:
    result = convert_to_cal_code("אבגדהוזחטיכךלמםנןסעפףצץקרת")

    assert result.cal_code == ")bgdhwzxTykklmmnns(ppccqrt"
    assert result.representation is InputRepresentation.HEBREW
    assert result.strategy is CalCodeConversionStrategy.HEBREW_TO_CAL_CODE


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("שׁלם", "$lm"),
        ("שׂלם", "&lm"),
    ],
)
def test_hebrew_shin_and_sin_are_distinguished_only_by_explicit_dot(
    value: str,
    expected: str,
) -> None:
    assert convert_to_cal_code(value).cal_code == expected


def test_bare_hebrew_shin_is_ambiguous() -> None:
    with pytest.raises(AmbiguousQueryError, match="shin|sin|ש"):
        convert_to_cal_code("שלם")


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


def test_syriac_consonants_map_to_cal_code() -> None:
    result = convert_to_cal_code("ܐܒܓܕܗܘܙܚܛܝܟܠܡܢܣܥܦܨܩܪܫܬ")

    assert result.cal_code == ")bgdhwzxTyklmns(pcqr$t"
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


def test_valid_explicit_cal_code_passes_through_without_reinterpretation() -> None:
    result = convert_to_cal_code(
        "mlk%",
        representation=InputRepresentation.CAL_CODE,
    )

    assert result.cal_code == "mlk%"
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

    assert result.cal_code == cal_code


@pytest.mark.parametrize("value", ["מלܟ", "mlk🙂", "mlk\n"])
def test_ambiguous_unsupported_or_control_input_fails_closed(value: str) -> None:
    with pytest.raises((AmbiguousQueryError, UnsupportedQueryError)):
        convert_to_cal_code(value)


@pytest.mark.anyio
async def test_public_conversion_tool_is_structured_and_local_only(
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

        response = await client.call_tool("cal_convert_to_code", {"value": "ܡܠܟ"})

    assert response.structured_content == {
        "original": "ܡܠܟ",
        "cal_code": "mlk",
        "representation": "syriac",
        "strategy": "syriac_to_cal_code",
    }
