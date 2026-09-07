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


def test_mandaic_letters_map_to_cal_mandaic_set() -> None:
    result = convert_to_cal_code("ࡀࡁࡂࡃࡄࡅࡆࡇࡈࡉࡊࡋࡌࡍࡎࡏࡐࡑࡒࡓࡔࡕࡖ")

    assert result.words[0].candidates == ("abgdhuzHTiklmns(pSqr$tD",)
    assert result.words[0].ambiguities == ()
    assert result.representation is InputRepresentation.MANDAIC
    assert result.strategy is CalCodeConversionStrategy.MANDAIC_TO_CAL_CODE


def test_mandaic_johnbook_24_3_shumh_fixture() -> None:
    result = convert_to_cal_code("ࡔࡅࡌࡇ")

    assert result.words[0].candidates == ("$umH",)
    assert result.words[0].ambiguities == ()


def test_mandaic_johnbook_24_3_dmanda_fixture() -> None:
    result = convert_to_cal_code("ࡖࡌࡀࡍࡃࡀ")

    assert result.words[0].candidates == ("Dmanda",)
    assert result.words[0].ambiguities == ()


def test_mandaic_kad_expands_deterministically_to_kd() -> None:
    result = convert_to_cal_code("ࡗ")

    assert result.words[0].candidates == ("kD",)
    assert result.words[0].ambiguities == ()


@pytest.mark.parametrize("value", ["ࡘ", "࡙", "࡚", "࡛", "࡜", "࡞"])
def test_mandaic_ain_marks_punctuation_and_unassigned_fail_closed(value: str) -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code(value)


def test_mixed_mandaic_and_samaritan_fails_closed() -> None:
    with pytest.raises(UnsupportedQueryError):
        convert_to_cal_code("ࡁࠁ")


@pytest.mark.anyio
async def test_public_conversion_tool_exposes_mandaic_kad_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("cal_convert_to_code must stay local-only")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    sys.modules.pop("cal_mcp.server", None)
    server_module = importlib.import_module("cal_mcp.server")

    async with Client(server_module.mcp, raise_exceptions=True) as client:
        response = await client.call_tool("cal_convert_to_code", {"value": "ࡗ"})

    assert response.structured_content == {
        "original": "ࡗ",
        "representation": "mandaic",
        "strategy": "mandaic_to_cal_code",
        "words": [
            {
                "original": "ࡗ",
                "candidates": ["kD"],
                "ambiguities": [],
            }
        ],
    }
