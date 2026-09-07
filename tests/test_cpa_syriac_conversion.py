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


def test_cpa_hor_407_3_fixture_uses_syriac_path() -> None:
    result = convert_to_cal_code("ܕܝܢ")

    assert result.words[0].candidates == ("dyn",)
    assert result.words[0].ambiguities == ()
    assert result.representation is InputRepresentation.SYRIAC
    assert result.strategy is CalCodeConversionStrategy.SYRIAC_TO_CAL_CODE


def test_dotless_dalath_rish_returns_both_cal_candidates() -> None:
    result = convert_to_cal_code("ܖܐ")

    assert result.words[0].candidates == ("d)", "r)")
    assert len(result.words[0].ambiguities) == 1
    ambiguity = result.words[0].ambiguities[0]
    assert ambiguity.index == 0
    assert ambiguity.input == "ܖ"
    assert ambiguity.cal_codes == ("d", "r")
    assert result.representation is InputRepresentation.SYRIAC
    assert result.strategy is CalCodeConversionStrategy.SYRIAC_TO_CAL_CODE


def test_six_dotless_dalath_rish_characters_exceed_candidate_bound() -> None:
    with pytest.raises(ConversionExpansionError):
        convert_to_cal_code("ܖܖܖܖܖܖ")


def test_final_semkath_maps_to_s() -> None:
    result = convert_to_cal_code("ܤ")

    assert result.words[0].candidates == ("s",)
    assert result.words[0].ambiguities == ()


def test_cpa_reversed_pe_remains_emphatic_p() -> None:
    result = convert_to_cal_code("ܧ")

    assert result.words[0].candidates == ("P",)
    assert result.words[0].ambiguities == ()


def test_unverified_yudh_he_remains_unsupported() -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code("ܞ")


@pytest.mark.anyio
async def test_public_conversion_tool_exposes_dotless_dalath_rish_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("cal_convert_to_code must stay local-only")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        response = await client.call_tool("cal_convert_to_code", {"value": "ܖ"})

    assert response.structured_content == {
        "original": "ܖ",
        "representation": "syriac",
        "strategy": "syriac_to_cal_code",
        "words": [
            {
                "original": "ܖ",
                "candidates": ["d", "r"],
                "ambiguities": [
                    {
                        "index": 0,
                        "input": "ܖ",
                        "cal_codes": ["d", "r"],
                    }
                ],
            }
        ],
    }
