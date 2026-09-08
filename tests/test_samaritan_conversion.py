from __future__ import annotations

import importlib
import socket
import sys

import pytest
from mcp import Client

from cal_mcp.normalization import (
    CalCodeAmbiguity,
    CalCodeConversionStrategy,
    ConversionExpansionError,
    InputRepresentation,
    UnsupportedQueryError,
    convert_to_cal_code,
)


def test_samaritan_letters_map_with_shan_ambiguity() -> None:
    result = convert_to_cal_code("ࠀࠁࠂࠃࠄࠅࠆࠇࠈࠉࠊࠋࠌࠍࠎࠏࠐࠑࠒࠓࠔࠕ")

    assert result.words[0].candidates == (
        ")bgdhwzxTyklmns(pcqr$t",
        ")bgdhwzxTyklmns(pcqr&t",
    )
    assert result.words[0].ambiguities == (
        CalCodeAmbiguity(index=20, input="ࠔ", cal_codes=("$", "&")),
    )
    assert result.representation is InputRepresentation.SAMARITAN
    assert result.strategy is CalCodeConversionStrategy.SAMARITAN_TO_CAL_CODE


def test_samaritan_gen_37_2_fixture_maps_to_cal_br() -> None:
    result = convert_to_cal_code("ࠁࠓ")

    assert result.words[0].candidates == ("br",)
    assert result.words[0].ambiguities == ()


def test_samaritan_six_shan_characters_exceed_candidate_bound() -> None:
    with pytest.raises(ConversionExpansionError):
        convert_to_cal_code("ࠔࠔࠔࠔࠔࠔ")


@pytest.mark.parametrize("value", ["ࠖ", "ࠚ", "ࠤ", "࠰", "࠿"])
def test_samaritan_marks_punctuation_and_unassigned_fail_closed(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


def test_mixed_samaritan_and_hatran_fails_closed() -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code("ࠁ𐣡")


@pytest.mark.anyio
async def test_public_conversion_tool_exposes_samaritan_ambiguity_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("cal_convert_to_code must stay local-only")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        response = await client.call_tool("cal_convert_to_code", {"value": "ࠔ"})

    assert response.structured_content == {
        "original": "ࠔ",
        "representation": "samaritan",
        "strategy": "samaritan_to_cal_code",
        "words": [
            {
                "original": "ࠔ",
                "candidates": ["$", "&"],
                "ambiguities": [
                    {
                        "index": 0,
                        "input": "ࠔ",
                        "cal_codes": ["$", "&"],
                    }
                ],
            }
        ],
    }
