from __future__ import annotations

import importlib
import socket
import sys

import pytest
from mcp import Client

from cal_mcp.normalization import (
    CalCodeConversionStrategy,
    ConversionExpansionError,
    InputRepresentation,
    UnsupportedQueryError,
    convert_to_cal_code,
)


def test_hatran_letters_map_with_daleth_resh_ambiguity() -> None:
    result = convert_to_cal_code("𐣠𐣡𐣢𐣣𐣤𐣥𐣦𐣧𐣨𐣩𐣪𐣫𐣬𐣭𐣮𐣯𐣰𐣱𐣲𐣴𐣵")

    assert result.words[0].candidates == (
        ")bgdhwzxTyklmns(pcq$t",
        ")bgrhwzxTyklmns(pcq$t",
    )
    assert result.words[0].ambiguities == (
        result.words[0].ambiguities[0],
    )
    ambiguity = result.words[0].ambiguities[0]
    assert ambiguity.index == 3
    assert ambiguity.input == "𐣣"
    assert ambiguity.cal_codes == ("d", "r")
    assert result.representation is InputRepresentation.HATRAN
    assert result.strategy is CalCodeConversionStrategy.HATRAN_TO_CAL_CODE


def test_hatran_h_71_fixture_maps_to_cal_klb() -> None:
    result = convert_to_cal_code("𐣪𐣫𐣡")

    assert result.words[0].candidates == ("klb",)
    assert result.words[0].ambiguities == ()


def test_hatran_six_daleth_resh_characters_exceed_candidate_bound() -> None:
    with pytest.raises(ConversionExpansionError):
        convert_to_cal_code("𐣣𐣣𐣣𐣣𐣣𐣣")


@pytest.mark.parametrize("value", ["𐣳", "𐣻", "𐣿"])
def test_hatran_unassigned_and_numbers_fail_closed(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


def test_mixed_hatran_and_nabataean_fails_closed() -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code("𐣪𐢕")


@pytest.mark.anyio
async def test_public_conversion_tool_exposes_hatran_ambiguity_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("cal_convert_to_code must stay local-only")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        response = await client.call_tool("cal_convert_to_code", {"value": "𐣣"})

    assert response.structured_content == {
        "original": "𐣣",
        "representation": "hatran",
        "strategy": "hatran_to_cal_code",
        "words": [
            {
                "original": "𐣣",
                "candidates": ["d", "r"],
                "ambiguities": [
                    {
                        "index": 0,
                        "input": "𐣣",
                        "cal_codes": ["d", "r"],
                    }
                ],
            }
        ],
    }
