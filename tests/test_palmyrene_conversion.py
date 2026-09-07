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


def test_palmyrene_letters_map_by_researched_character_identity() -> None:
    result = convert_to_cal_code("𐡠𐡡𐡢𐡣𐡤𐡥𐡦𐡧𐡨𐡩𐡪𐡫𐡬𐡭𐡮𐡯𐡰𐡱𐡲𐡳𐡴𐡵𐡶")

    assert result.words[0].candidates == (")bgdhwzxTyklmnn s(pcqr$t".replace(" ", ""),)
    assert result.words[0].ambiguities == ()
    assert result.representation is InputRepresentation.PALMYRENE
    assert result.strategy is CalCodeConversionStrategy.PALMYRENE_TO_CAL_CODE


def test_palmyrene_final_nun_and_nun_converge_to_cal_n() -> None:
    result = convert_to_cal_code("𐡭𐡮")

    assert result.words[0].candidates == ("nn",)


def test_palmyrene_pat992_fixture_maps_to_cal_qsm() -> None:
    result = convert_to_cal_code("𐡳𐡯𐡬")

    assert result.words[0].candidates == ("qsm",)
    assert result.words[0].ambiguities == ()


@pytest.mark.parametrize("value", ["𐡷", "𐡹"])
def test_palmyrene_fleuron_and_number_fail_closed(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


def test_mixed_palmyrene_and_imperial_aramaic_fails_closed() -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code("𐡬𐡌")


@pytest.mark.anyio
async def test_public_conversion_tool_exposes_palmyrene_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("cal_convert_to_code must stay local-only")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        response = await client.call_tool("cal_convert_to_code", {"value": "𐡳𐡯𐡬"})

    assert response.structured_content == {
        "original": "𐡳𐡯𐡬",
        "representation": "palmyrene",
        "strategy": "palmyrene_to_cal_code",
        "words": [{"original": "𐡳𐡯𐡬", "candidates": ["qsm"], "ambiguities": []}],
    }
