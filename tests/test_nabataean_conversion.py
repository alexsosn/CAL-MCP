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
)


def test_nabataean_letters_map_by_researched_character_identity() -> None:
    result = convert_to_cal_code("𐢀𐢁𐢂𐢃𐢄𐢅𐢆𐢇𐢈𐢉𐢊𐢋𐢌𐢍𐢎𐢏𐢐𐢑𐢒𐢓𐢔𐢕𐢖𐢗𐢘𐢙𐢚𐢛𐢜𐢝𐢞")

    assert result.words[0].candidates == ("))bbgdhhwzxTyykkllmmnns(pcqr$$t",)
    assert result.words[0].ambiguities == ()
    assert result.representation is InputRepresentation.NABATAEAN
    assert result.strategy is CalCodeConversionStrategy.NABATAEAN_TO_CAL_CODE


@pytest.mark.parametrize(
    ("final_form", "ordinary_form", "expected"),
    [
        ("𐢀", "𐢁", ")"),
        ("𐢂", "𐢃", "b"),
        ("𐢆", "𐢇", "h"),
        ("𐢌", "𐢍", "y"),
        ("𐢎", "𐢏", "k"),
        ("𐢐", "𐢑", "l"),
        ("𐢒", "𐢓", "m"),
        ("𐢔", "𐢕", "n"),
        ("𐢜", "𐢝", "$"),
    ],
)
def test_nabataean_contextual_final_forms_converge(
    final_form: str,
    ordinary_form: str,
    expected: str,
) -> None:
    final_result = convert_to_cal_code(final_form)
    ordinary_result = convert_to_cal_code(ordinary_form)

    assert final_result.words[0].candidates == (expected,)
    assert ordinary_result.words[0].candidates == (expected,)


def test_nabataean_nabtomb_8_2_fixture_maps_to_cal_dnh() -> None:
    result = convert_to_cal_code("𐢅𐢕𐢇")

    assert result.words[0].candidates == ("dnh",)
    assert result.words[0].ambiguities == ()


@pytest.mark.parametrize("value", ["𐢧", "𐢯"])
def test_nabataean_numbers_fail_closed(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


def test_mixed_nabataean_and_palmyrene_fails_closed() -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code("𐢅𐡬")


@pytest.mark.anyio
async def test_public_conversion_tool_exposes_nabataean_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("cal_convert_to_code must stay local-only")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        response = await client.call_tool("cal_convert_to_code", {"value": "𐢅𐢕𐢇"})

    assert response.structured_content == {
        "original": "𐢅𐢕𐢇",
        "representation": "nabataean",
        "strategy": "nabataean_to_cal_code",
        "words": [{"original": "𐢅𐢕𐢇", "candidates": ["dnh"], "ambiguities": []}],
    }
